# Copyright 2013 Mellanox Technologies, Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import setuptools

Name = 'eswitchd'
Url = ""
Version = 0.6
License = 'Apache License 2.0'
Author = 'Mellanox'
AuthorEmail = 'openstack@mellanox.com'
Maintainer = ''
Summary = 'Mellanox eswtich Daemon'
ShortDescription = Summary
Description = Summary

DataFiles = [
]

setuptools.setup(
    name=Name,
    version=Version,
    url=Url,
    author=Author,
    author_email=AuthorEmail,
    description=ShortDescription,
    long_description=Description,
    license=License,
    include_package_data=False,
    install_requires=["oslo.config","pyzmq"],
    packages=setuptools.find_packages('.'),
    data_files=DataFiles,
    entry_points={
        'console_scripts': [
            'eswitchd = eswitchd.eswitch_daemon:main',
            'ebrctl = eswitchd.cli.ebrctl:main',
        ]
    },
)
