#!/bin/env python
def transformXML(xmlfile):
  import xml.etree.ElementTree as et
  tree = et.parse(xmlfile)
  for ci in tree.findall("CollectionItem"):
    ciname = ci.get('NAME')  
    if ciname == str("UDM_FRA_USAGE") or ciname == str("UDM_DG_APPLY_LAG"):
      print "  Zetten attribuut COLLECT_WHEN_ALTSKIP "+ciname+"."
      ci.set('COLLECT_WHEN_ALTSKIP','TRUE')
      mcoll = ci.find("MetricColl")   
      sesysdbaflag = 'n'
      for seiprop in mcoll.findall("ItemProperty"):        
        if seiprop.text.lower() == str('sysdba'):
          sesysdbaflag = 'j'
      if sesysdbaflag == 'n':     
        print "    Toevoegen Role subelement."      
        seIP = et.SubElement(mcoll, 'ItemProperty', attrib={ 'NAME' : 'Role'})
        seIP.text = str('SYSDBA')       
  tree.write(xmlfile)   

  
if __name__ == "__main__":
  import os
  from os import path
  from optparse import OptionParser, OptionGroup

  parser = OptionParser(usage='Usage: %prog [options]')
  parser.add_option("-d", "--db-unique-name",  dest="dbuname", help="Gebruik deze optie om UDM voor een specifieke standby database de UDM aan te zetten. Let op: de parameterwaarde moet db_unique_name zijn en niet instance of db naam. VB: D105T_2", default=False)
  parser.add_option("-p", "--path",  dest="pathagentxml", help="Gebruik deze optie om de locatie van agent configuratie xml te bepalen. Default locatie is /u01/app/oracle/product/11.1.0/agent11g/sysman/emd/collection", default='/u01/app/oracle/product/11.1.0/agent11g/sysman/emd/collection')
  parser.description = '''Gebruik dit script om User defined metric (UDM_FRA_USAGE en UDM_DG_APPLY_LAG) op de standby database aan te zetten. 
VB:
  -- Pas alleen database D105T, D105T_2 is heeft standby role, uitvoeren op de standby server
  %prog -d D105T_2
  -- Pas voor alle standby db targets aan, uitvoeren op de standby server
  %prog

'''
  (options, args) = parser.parse_args()  

  configpath = options.pathagentxml
  if path.isdir(configpath):
    os.chdir(configpath)
    print 'Oracle agent database target config path: '+os.getcwd()
    import shutil
    import glob
    import time
    filebakext = '.'+time.strftime('%Y%m%d%H%M%S')+'.bak'
    if not options.dbuname:
      configfilefilter = str('oracle_database_*.xml')
    else:
      #parameter -d van toepassing
      configfilefilter = 'oracle_database_'+options.dbuname+'*.xml'
    configfiles = glob.glob(path.join(configpath,configfilefilter))
    for configfile in configfiles:
      print configfile+' wordt gebackupt en aangepast.'
      shutil.copy(configfile,configfile+filebakext)
      transformXML(configfile)
  else:
    print "Path niet aanwezig."
  

