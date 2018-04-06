#!/usr/bin/env python
##############################################################################
# Copyright (c) 2016 Daniel Farrell and Others.  All rights reserved.
#
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution,
# and is available at http://www.eclipse.org/legal/epl-v10.html
##############################################################################

import argparse
import sys

import lib

from deb import lib as deb_lib
from rpm import lib as rpm_lib

if __name__ == "__main__":
    # Accept a build definition via args
    parent_parser = argparse.ArgumentParser(
        add_help=False,
        description="Package OpenDaylight build as RPM/deb.")
    parent_parser._optionals.title = "Package type (required)"

    # All builds require a package-type arg
    pkg_type_group = parent_parser.add_mutually_exclusive_group(required=True)
    pkg_type_group.add_argument("--rpm", action="store_true",
                                help="package build as RPM")
    pkg_type_group.add_argument("--deb", action="store_true",
                                help="package build as deb")

    # All builds accept optional changelog name/email, sysd commit args
    opt_args_group = parent_parser.add_argument_group(
        "Additional config (optional)")
    opt_args_group.add_argument(
        "--sysd_commit", help="version of ODL systemd unit file to package")
    opt_args_group.add_argument("--changelog_name", default="Jenkins",
                                help="name of person who defined package")
    opt_args_group.add_argument("--changelog_email",
                                default="jenkins-donotreply@opendaylight.org",
                                help="email of person who defined package")

    # Use subparsers to accept args specific to build location
    subparsers = parent_parser.add_subparsers(
        title="Build location (required)")

    # Create subparser for defining builds directly from a URL
    direct_parser = subparsers.add_parser("direct",
                                          help="package build at URL")

    direct_parser._optionals.title = "Options"

    # Direct builds require a archive URL
    direct_parser.add_argument("--download_url", required=True,
                               help="URL to tar/zip build archive to package")

    direct_parser.add_argument("--service_file_url", required=False,
                               help="URL to .service file")

    direct_parser.add_argument("--distro_name_prefix", required=False,
                               help="Specify the distribution name. Default: "
                                    "'distribution-karaf' (OpenDaylight <7) or"
                                    "'karaf' (OpenDaylight >= 7). Example: "
                                    "'vpnservice-karaf'.")

    direct_parser.add_argument("--keep_distro_name", required=False,
                               help="Whether (True/False) to keep the "
                                    "original distribution (tar.gz) name when "
                                    "passing artifacts to rpmbuild.",
                               default=False)

    direct_parser.add_argument("--keep_service_file_name", required=False,
                               help="Whether (True/False) to keep the "
                                    "original file name/format of service "
                                    "file",
                               default=False)

    direct_parser.add_argument("--pkg_version", required=False,
                               help="Specify the version of the package "
                                    "to build. Default: 1.")

    direct_parser.add_argument("--pkg_distro", required=False,
                               help="Specify the distro of the package "
                                    "to build. "
                                    "Default: <automatically discovered>.")

    direct_parser.add_argument("--spec_template_path", required=False,
                             help="Path to spec file used in RPM/deb "
                                  "packaging")

    direct_parser.add_argument("--spec_template_type", required=False,
                             help="Templating engine spec is written in")

    direct_parser.add_argument("--clean_builddir", required=False,
                               help="Clean builddir before building a package",
                               default=True)

    direct_parser.add_argument("--extra_src_files", required=False,
                               help="Comma,delimited paths to files that will "
                                    "be copied to SOURCE in build directory")

    # Create subparser for building latest snapshot from a given branch
    latest_snap_parser = subparsers.add_parser(
        "latest_snap",
        help="package latest snapshot build of given major version")

    latest_snap_parser._optionals.title = "Options"

    # Latest-snapshot builds require a major version to pkg last build from
    latest_snap_parser.add_argument(
        "--major", required=True,
        help="major version to package latest snapshot from")

    # Print help if no arguments are given
    if len(sys.argv) == 1:
        parent_parser.print_help()
        sys.exit(1)

    # Extract passed args
    args = parent_parser.parse_args()

    # Build definition, populated below
    build = {}

    # Add changelog name to build definition
    if not args.changelog_name:
        # If empty string passed, as happens when a bash script calls this
        # script with unset var, use default
        build.update({"changelog_name": "Jenkins"})
    else:
        build.update({"changelog_name": args.changelog_name})

    # Add changelog email to build definition
    if not args.changelog_email:
        # If empty string passed, as happens when a bash script calls this
        # script with unset var, use default
        build.update(
            {"changelog_email": "jenkins-donotreply@opendaylight.org"})
    else:
        build.update({"changelog_email": args.changelog_email})

    # Depending on pkg type, add appropriate-format changelog date to build def
    if args.rpm:
        build.update({"changelog_date": lib.get_changelog_date("rpm")})
    if args.deb:
        build.update({"changelog_date": lib.get_changelog_date("deb")})

    # If hash of systemd unit file given add to build def, else use latest hash
    if args.sysd_commit:
        build.update({"sysd_commit": args.sysd_commit})
    else:
        build.update({"sysd_commit": lib.get_sysd_commit()})

    if args.spec_template_path:
        if args.spec_template_type:
            build.update({'spec_template_path': args.spec_template_path})
            build.update({'spec_template_type': args.spec_template_type})
        else:
            print("You have to specify spec_template_type along with " \
                  "spec_template_path")
            exit(1)

    if args.spec_template_type == 'cheetah' and not args.spec_template_path:
        print("You have to specify path to spec temlate file when using " \
              "Cheetah templating engine")
        exit(1)

    build.update({'clean_builddir': args.clean_builddir})

    if args.extra_src_files:
        build.update({'extra_src_files': args.extra_src_files})

    # Argparse rules imply args.major will only be present for latest_snap
    # builds and args.download_url will only be present for generic builds.
    # If doing a latest-snap build, find latest build tarball URL for given
    # major version and add to build definition. Else, add URL directly.
    if hasattr(args, "major"):
        build.update({"download_url": lib.get_snap_url(args.major)})
    else:
        build.update({"download_url": args.download_url})

    if hasattr(args, "pkg_version"):
        build.update({"pkg_version": args.pkg_version})

    if hasattr(args, "pkg_distro"):
        build.update({"pkg_distro": args.pkg_distro})

    # Use download_url to find pkg version, add to build def
    build.update(lib.extract_version(build["download_url"]))

    build.update({'service_file_url': args.service_file_url})
    build.update({'keep_service_file_name': args.keep_service_file_name})

    # Karaf 3 distros use distribution-karaf-, Karaf 4 uses karaf-
    build.update({"distro_name_prefix": args.distro_name_prefix or
        lib.get_distro_name_prefix(build['version_major'])})

    build.update({"keep_distro_name": args.keep_distro_name})

    # Update build definition with Java version required by ODL version
    build.update({"java_version": lib.get_java_version(
        build['version_major'])})

    # Use package-specific helper logic to do the specified build
    if args.rpm:
        rpm_lib.build_rpm(build)
    elif args.deb:
        deb_lib.build_deb(build)
