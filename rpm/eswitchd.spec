%global srcname eswitchd
%global package_name eswitchd
%global docpath doc/build/html

Name:       eswitchd
Version:    %{_eswitchd_version}
Release:    %{_eswitchd_release}%{dist}
Summary:    Mellanox eSwitch Daemon

Group:      Default
License:    ASL 2.0
Source0:    %{srcname}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-mock
BuildRequires:  python-neutron-tests
BuildRequires:  python-oslo-sphinx
BuildRequires:  python-pbr
BuildRequires:  python-setuptools
BuildRequires:  python-sphinx
BuildRequires:  python-testrepository
BuildRequires:  python-testtools

Requires:       python-babel
Requires:       python-pbr
Requires:       openstack-neutron-common
Requires:       python-zmq
Requires:       libvirt
Requires:       python-ethtool

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
%setup -q -n %{package_name}

%build
%{__python2} setup.py build

%install
export PBR_VERSION=%{version}
export SKIP_PIP_INSTALL=1
%{__python2} setup.py install --skip-build --root $RPM_BUILD_ROOT

install -d -m 755 %{buildroot}%{_localstatedir}/log/eswitchd
install -d -m 755 %{buildroot}%{_localstatedir}/run/eswitchd
install -d -m 755 %{buildroot}%{_sysconfdir}/eswitchd
install -d -m 755 %{buildroot}%{_sysconfdir}/eswitchd/rootwrap.d/
install -d -m 755 %{buildroot}%{_sysconfdir}/init.d
install -d -m 755 %{buildroot}%{_sysconfdir}/sudoers.d/
install -d -m 755 %{buildroot}%{_sysconfdir}/logrotate.d/

mv etc/eswitchd/eswitchd.conf %{buildroot}%{_sysconfdir}/eswitchd
mv etc/init.d/eswitchd %{buildroot}%{_sysconfdir}/init.d/eswitchd
mv etc/eswitchd/rootwrap.conf %{buildroot}%{_sysconfdir}/eswitchd
mv etc/eswitchd/rootwrap.d/eswitchd.filters %{buildroot}%{_sysconfdir}/eswitchd/rootwrap.d/eswitchd.filters
mv etc/sudoers.d/eswitch-sudoers %{buildroot}%{_sysconfdir}/sudoers.d/eswitch-sudoers
mv etc/logrotate.d/eswitchd %{buildroot}%{_sysconfdir}/logrotate.d/eswitchd
rm -rf %{buildroot}/usr/etc
rm -rf %{buildroo}%{python2_sitelib}/%{srcname}/tests

%clean
%{__rm} -rf %{buildroot}

%files
%doc README.rst
%{python2_sitelib}/%{srcname}
%{python2_sitelib}/%{srcname}-%{version}-py%{python2_version}.egg-info
%dir %attr(0755, eswitch, eswitch) %{_localstatedir}/run/eswitchd
%dir %attr(0755, eswitch, eswitch) %{_localstatedir}/log/eswitchd
%config(noreplace) %attr(0640, root, eswitch) %{_sysconfdir}/eswitchd/eswitchd.conf
%config %attr(0755, root, root) %{_sysconfdir}/eswitchd/rootwrap.conf
%config %attr(0644, root, root) %{_sysconfdir}/eswitchd/rootwrap.d/eswitchd.filters
%attr(0640, root, root) /etc/sudoers.d/eswitch-sudoers
%attr(0640, root, root) /etc/logrotate.d/eswitchd
%attr(0755, root, eswitch) %{_sysconfdir}/init.d/eswitchd
%attr(0755, root, root) /usr/bin/eswitchd-rootwrap
%attr(0550, root, eswitch) /usr/bin/eswitchd
%attr(0554, root, root) /usr/bin/ebrctl

