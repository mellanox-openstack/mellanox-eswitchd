#!/bin/sh
#
# eswitchd  Mellanox Eswitch Daemon 
#
# chkconfig:   - 98 02
# description: Support VLANs using Linux bridging
### END INIT INFO

. /etc/rc.d/init.d/functions

proj=eswitchd
prog=$proj
#exec="/usr/bin/$prog"
exec="/usr/bin/eswitchd"
config="/etc/$proj/eswitchd.conf"
pidfile="/var/run/$proj/$prog.pid"
logfile="/var/log/eswitchd/eswitchd.log"

[ -e /etc/sysconfig/$prog ] && . /etc/sysconfig/$prog

lockfile=/var/lock/subsys/$prog

start() {
    [ -x $exec ] || exit 5
    [ -f $config ] || exit 6
    echo -n $"Starting $prog: "
    #daemon --user quantum --pidfile $pidfile "$exec --log-file /var/log/$proj/$plugin.log --config-file /etc/$proj/$proj.conf --config-file $config &>/dev/null & echo \$! > $pidfile"
    daemon --pidfile $pidfile "$exec --config-file /etc/$proj/$proj.conf --log-file $logfile &>/dev/null & echo \$! > $pidfile"
    retval=$?
    echo
    [ $retval -eq 0 ] && touch $lockfile
    return $retval
}

stop() {
    echo -n $"Stopping $prog: "
    killproc -p $pidfile $prog
    retval=$?
    echo
    [ $retval -eq 0 ] && rm -f $lockfile
    return $retval
}

restart() {
    stop
    start
}

reload() {
    restart
}

force_reload() {
    restart
}

rh_status() {
    status -p $pidfile $prog
}

rh_status_q() {
    rh_status >/dev/null 2>&1
}


case "$1" in
    start)
        rh_status_q && exit 0
        $1
        ;;
    stop)
        rh_status_q || exit 0
        $1
        ;;
    restart)
        $1
        ;;
    reload)
        rh_status_q || exit 7
        $1
        ;;
    force-reload)
        force_reload
        ;;
    status)
        rh_status
        ;;
    condrestart|try-restart)
        rh_status_q || exit 0
        restart
        ;;
    *)
        echo $"Usage: $0 {start|stop|status|restart|condrestart|try-restart|reload|force-reload}"
        exit 2
esac
exit $?
