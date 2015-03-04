%global sname eswitchd

Name:       eswitchd
Version:    %{_eswitchd_version}
Release:    %{_eswitchd_release}%{dist}
Summary:    Mellanox eSwitch Daemon

Group:      Default
License:    ASL 2.0
Source0:    %{sname}-%{version}.tar.gz

BuildArch:  x86_64
Requires:   python-setuptools
Requires:   python-zmq
Requires:   libvirt
Requires:   python-ethtool
Requires:   sudo
Requires:   shadow-utils
Requires:   glibc-common
Requires(post):   chkconfig

BuildRequires: python-setuptools
BuildRequires: json-c
%if %{rhel} == 7
BuildRequires: systemd
%else
BuildRequires: zeromq
%endif

%description
Mellanox eSwitch Daemon

%pre
/usr/bin/getent group eswitch >/dev/null || /usr/sbin/groupadd -r eswitch
/usr/bin/getent passwd eswitch >/dev/null || /usr/sbin/useradd -r -g eswitch -d /var/lib/eswitch -s /bin/false eswitch

%preun
if [ $1 -eq 0 ] ; then
    # Package removal, not upgrade
    /sbin/service eswitchd stop >/dev/null 2>&1
    /sbin/chkconfig --del eswitchd

    /sbin/service eswitchd stop >/dev/null 2>&1
    /sbin/chkconfig --del eswitchd
fi

%post
    /sbin/chkconfig --add eswitchd
    /sbin/chkconfig eswitchd on

%postun
if [ $1 -ge 1 ] ; then
    # Package upgrade, not uninstall
    /sbin/service eswitchd condrestart >/dev/null 2>&1 || :
fi

%prep
%setup -q -n eswitchd
# Remove bundled egg-info
rm -rf eswitchd.egg-info
# let RPM handle deps
sed -i '/setup_requires/d; /install_requires/d; /dependency_links/d' setup.py

%build
%{__python} setup.py build

%install
%{__rm} -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

install -d -m 755 %{buildroot}%{_localstatedir}/log/eswitchd
install -d -m 755 %{buildroot}%{_localstatedir}/run/eswitchd
install -d -m 755 %{buildroot}%{_sysconfdir}/eswitchd
install -d -m 755 %{buildroot}%{_sysconfdir}/init.d
install -d -m 755 %{buildroot}%{_sysconfdir}/sysconfig

install -m 755 etc/eswitchd/eswitchd.conf %{buildroot}%{_sysconfdir}/eswitchd
install -m 755 etc/init.d/eswitchd %{buildroot}%{_sysconfdir}/init.d
install -m 755 etc/sysconfig/eswitchd %{buildroot}%{_sysconfdir}/sysconfig


install -d -m 755 %{buildroot}/usr/local/bin

# Install sudoers
install -D -m 440 etc/sudoers.d/eswitchd %{buildroot}%{_sysconfdir}/sudoers.d/eswitchd

install -m 755 etc/eswitchd/rootwrap.conf %{buildroot}%{_sysconfdir}/eswitchd

install -D -m 755 etc/eswitchd/rootwrap.d/eswitchd.filters %{buildroot}%{_sysconfdir}/eswitchd/rootwrap.d/eswitchd.filters

%check

%clean
%{__rm} -rf %{buildroot}

%files
%dir %attr(0755, eswitch, eswitch) %{_localstatedir}/run/eswitchd
%dir %attr(0755, eswitch, eswitch) %{_localstatedir}/log/eswitchd
%{python_sitelib}/eswitchd
%{python_sitelib}/*.egg-info
%config(noreplace) %attr(0640, root, eswitch) %{_sysconfdir}/eswitchd/eswitchd.conf
%config %attr(0755, root, eswitch) %{_sysconfdir}/init.d/eswitchd
%config %attr(0755, root, eswitch) %{_sysconfdir}/sysconfig/eswitchd
%config %attr(0440, root, root) %{_sysconfdir}/sudoers.d/eswitchd
%config %attr(0755, root, root) %{_sysconfdir}/eswitchd/rootwrap.conf
%config %attr(0644, root, root) %{_sysconfdir}/eswitchd/rootwrap.d/eswitchd.filters
/usr/bin/eswitch-rootwrap
/usr/bin/eswitchd
%attr(0744, root, root) /usr/bin/ebrctl

%changelog
* Thu Mar 3  2015 Openstack Team <openstack@mellanox.com> 0.11-1
  fix create pkey to support full pkey and partial pkey
  add support for rhel7

* Thu Jun 19 2014 Openstack Team <openstack@mellanox.com> 0.10-1
  Fixed eswitchd logging
  Fixed wrong error message when no PFs are found
  Fix for getting GUID index in 2.2
  Added fix to include ib_ipoib driver

* Thu Dec 12 2013 Openstack Team <openstack@mellanox.com> 0.7-1
  Running eswitch as eswitch user

* Mon Dec 02 2013 Openstack Team <openstack@mellanox.com> 0.6-1
- Bug fixes

* Fri Nov 25 2013 Openstack Team <openstack@mellanox.com> 0.5-1
- Bug fixes

* Mon Sep 16 2013 Openstack Team <openstack@mellanox.com> 0.4-1
- Bug fixes
- Configurable zmq url connections

* Thu May 02 2013 Openstack Team <openstack@mellanox.com> 0.1-1
- Initial Release

