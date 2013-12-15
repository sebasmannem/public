#!/bin/sh
apt-get install postgresql apache2 php5 libapache2-mod-php5 php5-cli php5-pgsql postfix dovecot-common drbd8-utils heartbeat bind9 vim autofs getmail4 nfs-common nfs-kernel-server openssh-server amavisd-new spamassassin clamav-daemon opendkim postfix-policyd-spf-python pyzor razor arj cabextract cpio lha nomarch pax rar unrar unzip zip ntp
adduser clamav amavis
adduser amavis clamav
update-rc.d postgresql disable
update-rc.d apache2 disable
update-rc.d nfs-kernel-server disable
[ -f /etc/default/spamassassin.org ] || ln /etc/default/spamassassin /etc/default/spamassassin.org
sed 's/^ENABLED=.*/ENABLED=1/' < /etc/default/spamassassin.org > /tmp/spamassassin
mv /tmp/spamassassin /etc/default/
/etc/init.d/spamassassin start

[ -f /etc/amavis/conf.d/15-content_filter_mode.org ] || ln /etc/amavis/conf.d/15-content_filter_mode /etc/amavis/conf.d/15-content_filter_mode.org
sed 's/^#@bypass_\(.*\)_checks_maps/@bypass_\1_checks_maps/;s/^#\( *\)\\\%bypass_virus_checks/\1\\\%bypass_virus_checks/' < /etc/amavis/conf.d/15-content_filter_mode > /tmp/15-content_filter_mode
mv /tmp/15-content_filter_mode /etc/amavis/conf.d/15-content_filter_mode
[ -f /etc/amavis/conf.d/20-debian_defaults.org ] || ln /etc/amavis/conf.d/20-debian_defaults /etc/amavis/conf.d/20-debian_defaults.org
sed 's/$final_spam_destiny\( *\)=.*/$final_spam_destiny\1= D_DISCARD;/' < /etc/amavis/conf.d/20-debian_defaults > /tmp/20-debian_defaults
grep -q '$sa_tag_level_deflt' /tmp/20-debian_defaults
if [ $? -ne 0 ]; then
  echo '
#Additionally, you may want to adjust the following options to flag more messages as spam: 
$sa_tag_level_deflt = -999; # add spam info headers if at, or above that level
$sa_tag2_level_deflt = 6.0; # add 'spam detected' headers at that level
$sa_kill_level_deflt = 21.0; # triggers spam evasive actions
$sa_dsn_cutoff_level = 4; # spam level beyond which a DSN is not sent' >> /tmp/20-debian_defaults
fi
mv /tmp/20-debian_defaults /etc/amavis/conf.d/20-debian_defaults

[ -f /etc/amavis/conf.d/50-user.org ] || ln /etc/amavis/conf.d/50-user /etc/amavis/conf.d/50-user.org
sed -e 's/$myhostname\( *= *\).*/$myhostname\1'"'82-169-176-248.ip.telfort.nl';/" -e 's/@local_domains_acl( *= *\).*/@local_domains_acl\1\( "mannem.nl" \);/' < /etc/amavis/conf.d/50-user > /tmp/50-user
grep -q '$myhostname' /tmp/50-user || echo "\$myhostname = '82-169-176-248.ip.telfort.nl';" >> /tmp/50-user
grep -q '@local_domains_acl' /tmp/50-user || echo '@local_domains_acl = ( "mannem.nl" );' >> /tmp/50-user
/etc/init.d/amavis restart
postconf -e 'content_filter = smtp-amavis:[127.0.0.1]:10024'
sed '' < /etc/postfix/master.cf > /tmp/master.cf
grep -q 'smtp-amavis' /tmp/master.cf || echo '
smtp-amavis     unix    -       -       -       -       2       smtp
        -o smtp_data_done_timeout=1200
        -o smtp_send_xforward_command=yes
        -o disable_dns_lookups=yes
        -o max_use=20

127.0.0.1:10025 inet    n       -       -       -       -       smtpd
        -o content_filter=
        -o local_recipient_maps=
        -o relay_recipient_maps=
        -o smtpd_restriction_classes=
        -o smtpd_delay_reject=no
        -o smtpd_client_restrictions=permit_mynetworks,reject
        -o smtpd_helo_restrictions=
        -o smtpd_sender_restrictions=
        -o smtpd_recipient_restrictions=permit_mynetworks,reject
        -o smtpd_data_restrictions=reject_unauth_pipelining
        -o smtpd_end_of_data_restrictions=
        -o mynetworks=127.0.0.0/8
        -o smtpd_error_sleep_time=0
        -o smtpd_soft_error_limit=1001
        -o smtpd_hard_error_limit=1000
        -o smtpd_client_connection_count_limit=0
        -o smtpd_client_connection_rate_limit=0
        -o receive_override_options=no_header_body_checks,no_unknown_recipient_checks' >> /tmp/master.cf

