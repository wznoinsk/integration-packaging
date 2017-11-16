#!/usr/bin/env python
"""Build RPM .spec files from build description and a Jinja2 .spec template."""

import os
import re
from string import Template
import Cheetah.Template as template_ch
import sys

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    sys.stderr.write("We recommend using our included Vagrant env.\n")
    sys.stderr.write("Else, do `pip install -r requirements.txt` in a venv.\n")
    raise

# Path to the directory that contains this file is assumed to be the spec dir
spec_dir = os.path.dirname(os.path.abspath(__file__))

def build_spec(build):
    """Build the RPM .spec file from a template for the given build description.

    :param build: Description of an RPM build
    :type build: dict
    :param env: Templating environment: jinja2, Cheetah

    """

    # Python string Template, specialized into a specfile file name per-build
    out_template = Template("opendaylight-$version_major.$version_minor."
                                 "$version_patch-$pkg_version.spec")

    if build['spec_template_type'] == 'jinja2':
        out_specfile_name = out_template.substitute(build)
        out_specfile_path = os.path.join(spec_dir, out_specfile_name)

        # Create the Jinja2 Environment
        env = Environment(loader=FileSystemLoader(spec_dir))

        # Load the OpenDaylight RPM .spec file Jinja2 template
        in_template = env.get_template("opendaylight.spec.j2")

        with open(out_specfile_path, "w") as specfile:
            specfile.write(in_template.render(build))

    elif build['spec_template_type'] == 'cheetah':

        build.update({'all_artifacts':
                        [os.path.basename(build['distro_tar_path']),
                         os.path.basename(build['unitfile_tar_path'])]})

        out_content = template_ch.Template(file=build['spec_template_path'],
                                             searchList=build).respond()
        out_content = out_content.encode('utf-8')

        # override Release param in spec file
        # run only when pkg_version/distro was specificed at CLI

        if build['pkg_version'] or build['pkg_distro']:
            out_content = re.sub(r"Release:.*", "Release: %s.%s" %
                                 (build['pkg_version'] or '',
                                  build['pkg_distro'] or ''), out_content)


        _version = re.search(r'(\d+)\.(\d+)\.(\d+)',
                             re.search('Version.*', out_content).group(0))

        if _version.group(1) != build['version_major']:
            build.update({'version_major': _version.group(1)})

        if _version.group(2) != build['version_minor']:
            build.update({'version_minor': _version.group(1)})

        out_specfile_name = out_template.substitute(build)
        out_specfile_path = os.path.join(spec_dir, out_specfile_name)

        with open(out_specfile_path, "w") as specfile:
            specfile.write(out_content)

        return out_specfile_path
