#!/bin/sh
logfile=test.log
[ $logfile ] && mv $logfile $logfile.prev


echo "Cleanup" | tee -a $logfile
rm /tmp/PWCrypt*

function RunCommand()
{
  echo "$1"
  echo -n "$1" >> $logfile
  $2 1>/tmp/test.$$.out.log 2>/tmp/test.$$.err.log
  Ret=$?
  [ $Ret -eq 0 ] && echo " > Success" >> $logfile || echo " > Error $Ret" >> $logfile
  echo "Output:" >>  $logfile
  awk '{print "  "$0}' /tmp/test.$$.out.log >> test.log
  if [ `cat /tmp/test.$$.err.log | wc -l` -gt 0 ]; then
    echo "Error:" >> $logfile
    awk '{print "  "$0}' /tmp/test.$$.err.log >> test.log
  fi
  rm /tmp/test.$$.err.log /tmp/test.$$.out.log
  [ $Ret -ne 0 ] && exit 1
}

RunCommand 'Compiling' 'gcc -Wall -lcrypt -lcrypto -o PWCrypt PWCrypt.c /lib64/libz.so.1'
mv PWCrypt /tmp
chmod 777 /tmp/PWCrypt
RunCommand 'Add first account' '/tmp/PWCrypt --hashmethod 5 --file /tmp/PWCrypt.db --account sebas --password uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu'
chmod 777 /tmp/PWCrypt.db
RunCommand 'Check first account' '/tmp/PWCrypt --passwdcheck --file /tmp/PWCrypt.db --account sebas --password uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu'
RunCommand 'Check first account' '/tmp/PWCrypt --passwdcheck --file /tmp/PWCrypt.db --account sebas'
#RunCommand 'Check first account' '/tmp/PWCrypt --passwdcheck --file /tmp/PWCrypt.db --account sebas --password uu'
RunCommand 'Add access to regine' '/tmp/PWCrypt --usergrant --file /tmp/PWCrypt.db --login regine'
RunCommand "Check for access of user regine." 'ssh regine@localhost /tmp/PWCrypt --file /tmp/PWCrypt.db --account sebas' 
RunCommand 'Remove access from regine' '/tmp/PWCrypt --userrevoke --file /tmp/PWCrypt.db --login regine' 
RunCommand 'Check for first account' '/tmp/PWCrypt --file /tmp/PWCrypt.db --account sebas'
RunCommand "Add second account" '/tmp/PWCrypt --file /tmp/PWCrypt.db --account sebaS --password gghhgg'
RunCommand "Alter password for first account" '/tmp/PWCrypt --file /tmp/PWCrypt.db --account sebas --password aabbccb'
RunCommand "Check for second account" '/tmp/PWCrypt --file /tmp/PWCrypt.db --account sebaS'
RunCommand "Check for first account" '/tmp/PWCrypt --file /tmp/PWCrypt.db --account sebas'
echo "Testscript finished succesfully..."

