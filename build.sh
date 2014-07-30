#!/bin/bash
# Copyright (c) 2014 Mellanox Technologies. All rights reserved.
#
# This Software is licensed under one of the following licenses:
#
# 1) under the terms of the "Common Public License 1.0" a copy of which is
#    available from the Open Source Initiative, see
#    http://www.opensource.org/licenses/cpl.php.
#
# 2) under the terms of the "The BSD License" a copy of which is
#    available from the Open Source Initiative, see
#    http://www.opensource.org/licenses/bsd-license.php.
#
# 3) under the terms of the "GNU General Public License (GPL) Version 2" a
#    copy of which is available from the Open Source Initiative, see
#    http://www.opensource.org/licenses/gpl-license.php.
#
# Licensee has the right to choose one of the above licenses.
#
# Redistributions of source code must retain the above copyright
# notice and one of the license notices.
#
# Redistributions in binary form must reproduce both the above copyright
# notice, one of the license notices in the documentation
# and/or other materials provided with the distribution.
readonly SUCCESS=0
readonly FAILURE=1
readonly RHEL_DIST="el"
readonly UBUNTU_DIST="ubuntu"
readonly REDHAT_FILE="/etc/redhat-release"
readonly UBUNTU_FIlE="/etc/os-release"
readonly BUILDDIR=/tmp/builddir
readonly PROJECT=eswitchd
readonly BUILD_SRC_DIR=${BUILDDIR}/${PROJECT}
readonly BUILDDIR_REPO=${BUILDDIR}/${REPONAME}
readonly CONFIG_DIR=etc
DIST=""


function check_version_environment() {
    if [ -z $ESWITCHD_VERSION ] ; then
        echo "missing ESWITCHD_VERSION in environment variable please add it"
        exit ${FAILURE}
    fi

    if [ -z $ESWITCHD_RELEASE ] ; then
        echo "missing ESWITCHD_RELEASE in environment variable, please add it"
        exit ${FAILURE}
    fi
}

function check_dist() {
    if [  -f ${REDHAT_FILE} ]; then
        DIST=${RHEL_DIST}
    elif  [  -f ${UBUNTU_FIlE} ]; then
        DIST=${UBUNTU_DIST}
    else
        echo "eswitchd Support only CentOS and Ubuntu"
        exit ${FAILURE}
    fi
}


function build_rpm(){
    mkdir -p ${BUILD_SRC_DIR}
    cp -a ${CONFIG_DIR} ${BUILD_SRC_DIR}
    cp -a ${PROJECT} ${BUILD_SRC_DIR}
    cp  setup.py ${BUILD_SRC_DIR}
    pushd ./
    cd ${BUILDDIR};tar zcvf ${PROJECT}-${ESWITCHD_VERSION}.tar.gz ${PROJECT}
    cp ${PROJECT}-${ESWITCHD_VERSION}.tar.gz ~/rpmbuild/SOURCES
    popd
    rpmbuild -ba --define "_eswitchd_version ${ESWITCHD_VERSION}" --define "_eswitchd_release ${ESWITCHD_RELEASE}" rpm/eswitchd.spec
    if [ $? != ${SUCCESS} ] ; then
        echo "Failed to build eswitchd rpm"
        exit ${FAILURE}
    fi

    cp /root/rpmbuild/RPMS/x86_64/eswitchd-${ESWITCHD_VERSION}-${ESWITCHD_RELEASE}.*.x86_64.rpm .
    if [ $? != ${SUCCESS} ] ; then
        echo "Failed to copy eswitchd rpm"
        exit ${FAILURE}
    fi

    cp /root/rpmbuild/SRPMS/eswitchd-${ESWITCHD_VERSION}-${ESWITCHD_RELEASE}.*.src.rpm .
    if [ $? != ${SUCCESS} ] ; then
        echo "Failed to copy source eswitchd rpm"
        exit ${FAILURE}
    fi
}

function update_deb_version(){
    sed "s/@@VERSION@@/${ESWITCHD_VERSION}/g;s/@@RELEASE@@/${ESWITCHD_RELEASE}/g" debian/changelog.template > debian/changelog
    if [ $? != ${SUCCESS} ] ; then
        echo "Failed to update deb version"
        exit ${FAILURE}
    fi
}

function build_deb(){
    cd deb
    rm -rf etc
    rm -rf eswitchd
    cp -rf ../etc .
    cp -rf ../eswitchd .
    cp -rf setup.py .
    update_deb_version
    dpkg-buildpackage -tc -uc -us
    if [ $? != ${SUCCESS} ] ; then
        echo "Failed to build eswitchd deb"
        exit ${FAILURE}
    fi
    rm -rf etc
    rm -rf eswitchd
    rm -rf setup.py
}

check_version_environment
check_dist
if [ $DIST == $RHEL_DIST ]; then
    build_rpm
elif [ $DIST == $UBUNTU_DIST ]; then
    build_deb
fi


exit ${SUCCESS}