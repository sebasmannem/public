#define _GNU_SOURCE         /* See feature_test_macros(7) */
#include <stdio.h>
//int asprintf(char **strp, const char *fmt, ...);
//int fprintf(FILE *stream, const char *format, ...);
//int fscanf(FILE *stream, const char *format, ...);
//int printf(const char *format, ...);
//int puts(const char *s);

#include <unistd.h>
//char *crypt(const char *key, const char *salt);
//int gethostname(char *name, size_t namelen);

#include <stdlib.h>
//int rand(void);
//void srand(unsigned int seed);
//void *malloc(size_t size);
//void free(void *ptr);
//void *realloc(void *ptr, size_t size);

#include <time.h>
//time_t time(time_t *tloc);

#include <zlib.h>
//ZEXTERN gzFile ZEXPORT gzopen OF((const char *path, const char *mode));
//ZEXTERN int ZEXPORT gzputc OF((gzFile file, int c));
//ZEXTERN int ZEXPORT gzgetc OF((gzFile file));
//ZEXTERN int ZEXPORT gzread OF((gzFile file, voidp buf, unsigned len));
//ZEXTERN int ZEXPORT gzwrite OF((gzFile file, voidpc buf, unsigned len));
//ZEXTERN int ZEXPORT gzflush OF((gzFile file, int flush));
//ZEXTERN int ZEXPORT gzclose OF((gzFile file));

#include <errno.h>

#define DEBUGLEVEL 1

struct keyFile
  {
  gzFile Handle;
  char *Name;
  char *Contents;
  char **Rows;

  int Size;
  int NumLines;
  int NumOrgLines;
  int isDirty;
  char HashMethod;
  int KeyStart;
  };

struct Row
  {
  char *Row;
  char *ID;
  signed char Key[4];
  char *Salt;
  char *Value;
  };

size_t strlen (char *s)
  {
  int i;
  i = 0;
  while (s[i] != '\0' && i < (2147483648))
    {i++;}
  return i;
  }

int strcmp(char *s1, char *s2)
  {
  int i;
  i=0;
  while (s1[i] != '\0' && s2[i] != '\0')
    {
    if (s1[i] == s2[i])
      {i++;}
    else if (s1[i] < s2[i])
      {return -1;}
    else
      {return 1;}
    }
  if (s1[i] != '\0')
    {return 1;}
  else if (s2[i] != '\0')
    {return -1;}
  else
    {return 0;}
  }

char *substring(char *string, int start, int length)
  {
  char *tmp;
  int stringlength, i;
  stringlength = strlen(string);

  if (length < 1)
    {
    length = stringlength + length;
    if (length < 0)
      {length = 0;}
    }
  if (start > stringlength)
    {
    start = stringlength;
    length = 0;
    }
  if (start + length > stringlength)
    {length = stringlength - start;}

  tmp=(char *) malloc (length+1);
  if (!tmp) 
    {
    fprintf(stderr, "Malloc error. Probably not enough memory.\n");
    exit(1);
    }
  for (i=0 ; i < length ; i++)
    {tmp[i] = string[start + i];}
  tmp[length]= '\0';

  return tmp;
  }

char *RndString(int length, char *ValidChars)
  {
  int i,val;
  static unsigned int offset = 0;
  //Temp for return value
  char *tmp;
  tmp = (char *) malloc (length + 1);
  if (!tmp)  
    {
    fprintf(stderr, "Malloc error. Probably not enough memory.\n");
    exit(1);
    }
 
  //Seed number for rand()
  srand((unsigned int) offset + time(0) + getpid());
  offset+=2;
 
  //ASCII characters 33 to 126
  for (i=0 ; i< length; i++)
    {
    val = rand() % strlen(ValidChars);
    tmp[i] = ValidChars[val];
    srand(rand());
    }

  tmp[length] = '\0';
 
  return tmp;
  }

int Scramble(signed char key[4], char *myString)
  {
  unsigned int i, x, y;

  for (i=0 ; i < strlen(myString) ; i++)
    {
    if ( myString[i] < 32 || myString[i] > 126 ) {return i + 1;}
    x = i % 255 + 1;
    y = key[0]*x*x*x + key[1]*x*x + key[2]*x + key[3];
    myString[i] = ((y + myString[i] - 35) % 95) + 32;
    }
  return strlen(myString);
  }

int HashLength(char Method)
  {
  switch( Method )
    {
    //Method -1 is geen encryptie
    case '0': return 13; //DES
    case '1': return 22; //MD5
    case '5': return 43; //SHA-256
    case '6': return 86; //SHA-512
    default : return -1;
    }
  }

char *Hash(char Method, char *Salt, char *Value)
  {
  char *Salt2, *Hashed, *Ret;
  int HashLen, SaltLen, RetLen, i, j;
  HashLen=HashLength(Method);

  if (HashLen < 0)
    {return Value;}
  else if (Method == '0')
    {
    Salt2 = Salt;
    }
  else
    {
    Salt2=(char *) malloc(21);
    if (!Salt2)  
      {
      fprintf(stderr, "Malloc error. Probably not enough memory.\n");
      exit(1);
      }
    asprintf(&Salt2, "$%c$%s$", Method, substring(Salt, 0, 16));
    }
  Hashed = crypt(Value, Salt2);

  if (Method != '0')
    {
    SaltLen=-1;
    j=0;
    for (i=0 ; i<strlen(Hashed) ; i++)
      {
      if (Hashed[i] == '$')
        {j++;}
      if (j>2)
        {
        SaltLen=i+1;
        break;
        }
      }
    Ret = substring(Hashed, SaltLen, 0);
    }
  else
    {Ret = Hashed;}
  RetLen = strlen(Ret);
  if (RetLen != HashLen)
    {
#if DEBUGLEVEL>0
      fprintf(stderr, "Length of hash (%i) is other the expected (%i)\n", RetLen, HashLen);
#endif
    }

  if (Method != '0')
    {free(Salt2);}
  return Ret;
  }

void SeekRow(struct Row *myRow, struct keyFile *myFile)
  {
  int i, j, LenRowID;
  char *tmp;
  LenRowID=strlen(myRow->ID);
#if DEBUGLEVEL>0
  fprintf(stderr, "Searching for Row with RowID=%s.\n", myRow->ID);
#endif
  for (i=0 ; i<myFile->NumLines ; i++)
    {
#if DEBUGLEVEL>0
    fprintf(stderr, "%i:", i);
#endif
    tmp = substring(myFile->Rows[i], 0, LenRowID);
#if DEBUGLEVEL>0
    fprintf(stderr, "%s", tmp);
#endif    
    if (strcmp(tmp, myRow->ID) == 0)
      {
      myRow->Row = myFile->Rows[i];
      myRow->Value = myRow->Row + myFile->KeyStart;
      if (strlen(myRow->Value) == 20)
        {
        myRow->Salt = substring(myRow->Value, 4, 16);
        for (j=0 ; j<4 ; j++)
          {
          myRow->Key[j] = myRow->Row[j+myFile->KeyStart];
          }
        }
      else
        {
        }
#if DEBUGLEVEL>0
      fprintf(stderr, "=OK\nRowValue=%s.\n", myRow->Value);
#endif
      break;
      }
    else
      {
#if DEBUGLEVEL>0
      fprintf(stderr, "=NOK\n");
#endif    
      }
    }
  free(tmp);
  }

int RemoveRow(char *RowID, struct keyFile *myFile)
  {
  int i, Ret, LenRowID, Cmp;
  char *tmp;
  LenRowID=strlen(RowID);
  Ret=0;
#if DEBUGLEVEL>0
  fprintf(stderr, "Searching for Row with RowID=%s.\n", RowID);
#endif    
  for (i=0 ; i<myFile->NumLines ; i++)
    {
#if DEBUGLEVEL>0
    fprintf(stderr, "%i:", i);
#endif    
    tmp = substring(myFile->Rows[i], 0, LenRowID);
    Cmp = strcmp(tmp, RowID);
//    free(tmp);
#if DEBUGLEVEL>0
    fprintf(stderr, "%s", tmp);
#endif    
    if (Cmp == 0)
      {
      Ret = strlen(myFile->Rows[i]) + 1;
      myFile->Rows[i] = "";
#if DEBUGLEVEL>0
      fprintf(stderr, "=DELETED\n");
#endif    
      break;
      }
    else
      {
#if DEBUGLEVEL>0
      fprintf(stderr, "=NOK\n");
#endif    
      }
    }
  return Ret;
  }

void GenKey(signed char Key[4])
  {

  int i, val;
  static unsigned int offset = 1;

  //Seed number for rand()
  srand((unsigned int) offset + time(0) + getpid());
  offset+=2;
  
  //ASCII characters 33 to 126
  for (i=0 ; i<4 ; i++)
    {
    val = rand() % 94;
    Key[i] = 33 + val;
    srand(rand());
    }
  }

char *CalcRow(char *RowID, signed char Key[4], char *Salt)
  {
  char *Row;
  Row = (char *) malloc(strlen(RowID) + strlen(Salt) +5);
  if (!Row)
    {
    fprintf(stderr, "Malloc error. Probably not enough memory.\n");
    exit(1);
    }
  asprintf(&Row, "%s%c%c%c%c%s", RowID, Key[0], Key[1], Key[2], Key[3], Salt);
  return Row;
  }

char *GenRow(char *RowID, char *ValidChars)
  {
  char *Row, *RandomText;
  signed char Key[4];
  Row = (char *) malloc(strlen(RowID) + 17);
  if (!Row)  
    {
    fprintf(stderr, "Malloc error. Probably not enough memory.\n");
    exit(1);
    }
  GenKey(Key);
  RandomText=RndString(16, ValidChars);
  Row = CalcRow(RowID, Key, RandomText);
  return Row;
  }

char *CalcPRow(char *RowID, char *PW)
  {
  char *Row;
  Row = (char *) malloc(strlen(RowID) + strlen(PW) + 1);
  if (!Row)  
    {
    fprintf(stderr, "Malloc error. Probably not enough memory.\n");
    exit(1);
    }
  asprintf(&Row, "%s%s", RowID, PW);
  return Row;
  }

void help(char *App)
  {
  printf("This is the security enhanced version of the existing gapw.\n");
  printf("Instead of a plain text (ini) file, this version uses hashing of accounts and encryption of passwords.\n");
  printf("The real login must be granted access to the database key (--usergrant) before it can access contents.\n\n");

  printf("Password management:\n");
  printf("-> Write out password: %s [--passwdwrite] --file [path to file] --account [account of password] --password [new password]\n", App);
  printf("-> Read back password: %s [--passwdread] --file [path to file] --account [account of password]\n", App);
  printf("-> Check existence of password: %s --passwdcheck --file [path to file] --account [account] [--password [expected password]]\n", App);
  printf("   If --password is supplied, then the check includes the password itself. Withoud --password only existence is checked.\n\n");

  printf("Login management:\n");
  printf("-> Grant access to login: %s --usergrant --file [path to file] --login [login to grant access].\n", App);
  printf("-> Revoke access from login: %s --userrevoke --file [path to file] --login [login to revoke access].\n", App);
  printf("-> Check access of login: %s --usercheck --file [path to file] --login [login to check].\n\n", App);

  printf("Optionally you can specify --hashmethod, to manually select another hash method.\n");
  printf("This has only effect on creation of new file (--passwdwrite, with non-existing file).\n");
  printf("The following options are available: 0 (DES), 1 (MD5, default), 5 (SHA-256), 6 (SHA-512).\n");
  printf("Higher value will result in (a little) more security, but larger database files.\n");

  }

int main (int argc, char *argv[])
  {
  //Werking: 
  // In het bestand (de wachtwoorden database) staan 3 belangrijke regels:
  // - De User regel, bestaande uit URowID (43), UKey (4) en USalt (16)
  // - De Entry regel, bestaande uit ERowID (43), EKey (4) en ESalt (16), waarbij EKey en ESalt samen zijn versleuteld middels UKey.
  // - De Password regel, bestaande uit PRowID (43), en het wachtwoord versleuteld middels EKey.
  // De genoemde regels staan altijd in deze volgorde in het bestand.
  //
  //Instellen: PWCrypt [DB File] [user@object] [password]
  // - Als het bestand niet bestaat, dan wordt een leeg bestand aangemaakt.
  // - Het bestand wordt in een array in het geheugen geladen.
  // - De username wordt met DefSalt gehashed. Het resultaat (URowID) identificeert de User regel en deze wordt in het bestand (array) opgezocht.
  // - Als de User regel niet bestaat, dan wordt UKey en USalt gegenereerd, hiermee wordt de userregel opgebouwd 
  //   en deze wordt aan het bestand (array) aan het einde toegevoegd.
  // - De Entry ([user@object]), wordt middels USalt gehashed. Het resultaat (ERowID) identificeert de Entry regel 
  //   en deze wordt in het bestand (array) opgezocht.
  // - Als de Entry regel niet bestaat, dan wordt EKey en ESalt gegenereert, en deze worden samen versleuteld middels uKey. 
  //   Het resultaat wordt achter ERowID geplakt en vormt de Entry regel, welke aan het bestand (array) aan het einde wordt toegevoegd.
  // - Het gespecificeerde Password wordt versleuteld middels de EKey.
  // - ESalt wordt gehashed met USalt. Het resultaat (PRowID) identificeert de Password regel en deze wordt in het bestand (array) opgezocht.
  // - Als de Password regel bestaat, dan wordt de regel verwijderd.
  // - De nieuwe Password regel wordt opgebouwd middels de PRowID en het versleutelde wachtwoord en wordt aan het einde van het bestand (array) toegevoegd.
  // - De array wordt naar het bestand weg geschreven.
  //
  //Uitlezen: PWCrypt [DB File] [user@object]
  // - De username wordt met DefSalt gehashed. Het resultaat (URowID) identificeert de User regel en deze wordt in het bestand opgezocht.
  // - De Userregel bestaat uit URowID (43), UKey (4) en USalt (16).
  // - De Entry ([user@object]), wordt middels USalt gehashed. Het resultaat (ERowID) wordt in het bestand opgezocht en identificeert de Entry regel.
  // - De Entry regel bestaat uit ERowID (43), EKey (4) en ESalt (16), waarbij EKey en ESalt samen zijn versleuteld middels UKey.
  // - Na ontsleutelen van EKey en ESalt wordt ESalt gehashed met USalt tot de PRowID.
  // - Middels PRowID wordt de Password Regel opgezocht.
  // - De Password regel bestaat uit PRowID (43), PWCrypt (rest), waarbij PWCrypt is versleuteld middels EKey.
  // - Na het ontsleutelen van PWCrypt is het wachtwoord beschikbaar.
  //
  int i, j, val, ret, Action=0;
  char *UserName=0, *Entry=0, *Password=0, *Login=0;
  char *defSalt=0;
  char *tmp=0;
  char SaltChars[65];

/*
struct Contents
  {
  gzFile Handle;
  char *Name;
  char *Contents;
  char **Rows;

  int Size;
  int NumLines;
  int NumOrgLines;
  int isDirty;
  char HashMethod;
  };

*/
  struct keyFile myFile = {0, 0, 0, 0, 0, 0, 0, 0, '\0', 0};
/*
struct Row
  {
  char *Row;
  char *ID;
  signed char Key[4];
  char *Salt;
  char *Value;
  };
*/

  struct Row URow = {0, 0, "\0\0\0", 0, 0};
  struct Row ERow = {0, 0, "\0\0\0", 0, 0};
  struct Row PRow = {0, 0, "\0\0\0", 0, 0};

  for (i=1 ; i < argc ; i++)
    {
    if (Action != 0 && (strcmp(substring(argv[i], 8, 0), "--passwd") == 0 || strcmp(substring(argv[i], 6, 0), "--user") == 0))
      {
      fprintf(stderr, "Cannot supply multiple actions (e.a. --passwdwrite --passwdread).\n");
      return 1;
      }

    if (strcmp(argv[i], "--passwdwrite") == 0)
      {Action = 1;}
    else if (strcmp(argv[i], "--passwdread") == 0)
      {Action = 2;}
    else if (strcmp(argv[i], "--passwdcheck") == 0)
      {Action = 3;}
    else if (strcmp(argv[i], "--usergrant") == 0)
      {Action = 4;}
    else if (strcmp(argv[i], "--userrevoke") == 0)
      {Action = 5;}
    else if (strcmp(argv[i], "--usercheck") == 0)
      {Action = 6;}
    else if (strcmp(argv[i], "--bulkload") == 0)
      {Action = 7;}
    else
      {
      if (i+1==argc)
        {
        fprintf(stderr, "Invalid parameter or parameter without value:%s.\n\n", argv[i]);
        help(argv[0]);
        return 1;
        }
      tmp=argv[i+1];
      if (strcmp(argv[i], "--file") == 0)
        {myFile.Name = tmp;}
      else if (strcmp(argv[i], "--hashmethod") == 0)
        {myFile.HashMethod=tmp[0];}
      else if (strcmp(argv[i], "--account") == 0)
        {Entry=tmp;}
      else if (strcmp(argv[i], "--password") == 0)
        {Password=tmp;}
      else if (strcmp(argv[i], "--login") == 0)
        {Login=tmp;}
      i++;
      }
    }

  if (!myFile.Name)
    {
    fprintf(stderr, "No passwordfile was specified.\n");
    help(argv[0]);
    return 1;
    }
  if (Password)
    {
    if (Action==0)
      {Action=1;}
    else if (Action!=1 && Action!=3)
      {fprintf(stderr, "Password was supplied without reason...\n");}
    }
  if (Entry)
    {
    if (Action==0)
      {Action=2;}
    else if (Action>3)
      {
      fprintf(stderr, "Account was supplied without reason...\n");
      free(Entry);
      Entry=0;
      }
    }
  if (Login)
    {
    if (Action==0)
      {Action=6;}
    else if (Action<4 || Action == 7)
      {fprintf(stderr, "Login was supplied without reason...\n");}
    }
  if (Action==0)
    {
    fprintf(stderr, "Not enough info was supplied.\n");
    help(argv[0]);
    }
  if (myFile.HashMethod>0 && Action != 1)
    {fprintf(stderr, "Hashmethod was supplied without reason...\n");}
  // SaltChars bevat alle hoofdletter, kleine letters, getallen '.' en '/'.
  // Dit wordt gebruikt voor het genereren van bijvoorbeeld een Salt.
  for (i=0 ; i<62; i++)
    {
    if (i<10)
      {SaltChars[i] = i+48;} //0-9
    else if (i < 36)
      {SaltChars[i] = i+55;} //A-Z
    else
      {SaltChars[i] = i+61;} //a-z
    }
  SaltChars[62] = '.';
  SaltChars[63] = '/';
  SaltChars[64] = '\0';

#if DEBUGLEVEL>0
  fprintf(stderr, "Opening file %s.\n", myFile.Name);
#endif    
  myFile.Handle=gzopen(myFile.Name, "rb");
  if (myFile.Handle)
    {
#if DEBUGLEVEL>0
    fprintf(stderr, "Reading HashMethod from file %s.\n", myFile.Name);
#endif
    myFile.HashMethod=gzgetc(myFile.Handle);
    myFile.KeyStart = HashLength(myFile.HashMethod);
#if DEBUGLEVEL>0
    fprintf(stderr, "HashMethod is %c.\n", myFile.HashMethod);
#endif

    myFile.Size=0;
    j = 1;
    for (i=1 ; i < 5 ; i++)
      {
      myFile.Size = myFile.Size + gzgetc(myFile.Handle) * j;
      j = j * 256;
      }
#if DEBUGLEVEL>0
    fprintf(stderr, "Alloc character array of %i bytes.\n", myFile.Size);
#endif    

    myFile.Contents=malloc(myFile.Size+1);
    if (!myFile.Contents)
      {
      fprintf(stderr, "Malloc error. Probably not enough memory.\n");
      exit(1);
      }
    i=gzread(myFile.Handle, myFile.Contents, myFile.Size+1);
    if ( i != myFile.Size)
      {
      if (i>myFile.Size)
        {fprintf(stderr, "Corrupted datafile. Uncompressed datasize (at least %i) is larger then was recorded in file header (%i)...\n", i, myFile.Size);}
      else
        {fprintf(stderr, "Corrupted datafile. Uncompressed datasize (%i) was not properly recorded in file header (%i)...\n", i, myFile.Size);}
      return 2;
      }
    i = sizeof(char*) * (4 + myFile.Size / myFile.KeyStart);
#if DEBUGLEVEL>0
    fprintf(stderr, "Allocating %i bytes of memory for pointers to rows.\n", i);
#endif    
    myFile.Rows = malloc(i);
    if (!myFile.Rows)  
      {
      fprintf(stderr, "Malloc error. Probably not enough memory.\n");
      exit(1);
      }
    myFile.Rows[0] = myFile.Contents;
    myFile.NumLines = 1;
    for (j=0 ; j < myFile.Size-1 ; j++)
      {
      if ( myFile.Contents[j] == '\0' && myFile.Contents[j+1] != '\0' )
        {
        myFile.Rows[myFile.NumLines] = myFile.Contents + j + 1;
#if DEBUGLEVEL>0
        fprintf(stderr, "Line %i: %s\n", myFile.NumLines-1, myFile.Rows[myFile.NumLines-1]);
#endif    
        myFile.NumLines++;
        }
      }
#if DEBUGLEVEL>0
    fprintf(stderr, "Line %i: %s\n", myFile.NumLines-1, myFile.Rows[myFile.NumLines-1]);
    fprintf(stderr, "Number of Lines %i.\n", myFile.NumLines);
#endif    

    myFile.NumOrgLines = myFile.NumLines;
    i = sizeof(char*) * (myFile.NumLines+3);
#if DEBUGLEVEL>0
    fprintf(stderr, "Realloc %i bytes for lines array (%i lines).\n", i, myFile.NumLines+3);
#endif    
    myFile.Rows=realloc(myFile.Rows, i);
    myFile.isDirty=0;
    ret = gzclose(myFile.Handle);
    if (ret != Z_OK)
      {
      fprintf(stderr, "Error %i occurred on closing the file.\n", ret);
      return 1;
      }
    myFile.Handle = 0;
    }
  else if (Action != 1)
    {
    fprintf(stderr, "Could not find file...\n");
    return 3;
    }
  else
    {
    fprintf(stderr, "Could not find file. New file will be created.\n");
    if (myFile.HashMethod=='\0')
      {myFile.HashMethod='1';}
    myFile.KeyStart = HashLength(myFile.HashMethod);
    if (myFile.KeyStart<0)
      {
      fprintf(stderr, "Invalid value '%c' was specified for parameter --hashmethod.\n", myFile.HashMethod);
      return 1;
      }

    myFile.Rows=malloc(3 * sizeof(char*));
    if (!myFile.Rows)  
      {
      fprintf(stderr, "Malloc error. Probably not enough memory.\n");
      exit(1);
      }
    
    myFile.NumLines = 0;
    myFile.Size = 0;
    }

  // defSalt bevat de standaard Salt die binnen het programma voor hashing wordt gehanteerd.
  // Middels deze standaard HASH wordt de gebruikersnaam gehashed tot een unieke User HASH (USalt).
  // USalt bevat de Standaard Salt die verder door deze gebruiker wordt gebruikt voor het maken van SHA-256 Hashes.
  if (myFile.HashMethod=='0')
    {
    defSalt = "GP";
    }
  else
    {
    defSalt = (char *) malloc(21);
    if (!defSalt)
      {
      fprintf(stderr, "Malloc error. Probably not enough memory.\n");
      exit(1);
      }
    defSalt[0] = '$';
    defSalt[1] = myFile.HashMethod;
    defSalt[2] = '$';
    for (i=0 ; i<16 ; i++)
      {
      val = (i * 11) % strlen(SaltChars);
      defSalt[i + 3] = SaltChars[val];
      }
    defSalt[19] = '$';
    defSalt[20] = '\0';
    }
#if DEBUGLEVEL>0
  fprintf(stderr, "DefSalt is: %s.\n", defSalt);
#endif

  UserName = getlogin();
  URow.ID = Hash(myFile.HashMethod, defSalt, UserName);
#if DEBUGLEVEL>0
  fprintf(stderr, "Crypt Username is: %s.\n", URow.ID);
#endif

  if (myFile.NumLines>0)
    {
#if DEBUGLEVEL>0
  fprintf(stderr, "Searching for URow (URowID=%s).\n", URow.ID);
#endif
    SeekRow(&URow, &myFile);
    }

  if (URow.Row)
    {
#if DEBUGLEVEL>0
    fprintf(stderr, "URow is found: %s\n", URow.Row);
#endif    
    }
  else
    {
#if DEBUGLEVEL>0
    fprintf(stderr, "Generating URow.\n");
#endif    
    GenKey(URow.Key);

    URow.Salt=RndString(16, SaltChars);
    Scramble (URow.Key, URow.Salt);
    URow.Row = CalcRow(URow.ID, URow.Key, URow.Salt);

#if DEBUGLEVEL>0
    fprintf(stderr, "URow=%s (generated).\n", URow.Row);
#endif    
    myFile.Rows[myFile.NumLines] = URow.Row;
    myFile.Size = myFile.Size+strlen(URow.Row) + 1;
#if DEBUGLEVEL>0
    fprintf(stderr, "URow added to contents.\n");
#endif    
    myFile.NumLines++;
    }

  for (i=0 ; i<4 ; i++)
    {URow.Key[i] = 0 - URow.Row[i+myFile.KeyStart];}
  Scramble (URow.Key, URow.Salt);

  if (Entry)
    {
#if DEBUGLEVEL>0
    fprintf(stderr, "Calculating ERow.ID (using USalt %s).\n", URow.Salt);
#endif

    ERow.ID = Hash(myFile.HashMethod, URow.Salt, Entry);

#if DEBUGLEVEL>0
    fprintf(stderr, "Searching for ERow (ERowID=%s).\n", ERow.ID);
#endif    
    SeekRow(&ERow, &myFile);

    if (ERow.Row)
      {
#if DEBUGLEVEL>0
      fprintf(stderr, "ERow=%s (found).\n", ERow.Row);
#endif
      }
    else
      {
      if (Action == 1)
        {
#if DEBUGLEVEL>0
        fprintf(stderr, "Generating ERow.\n");
#endif
        ERow.Row = GenRow(ERow.ID, SaltChars);
#if DEBUGLEVEL>0
        fprintf(stderr, "ERow=%s (calculated).\n", ERow.Row);
#endif
        myFile.Rows[myFile.NumLines] = ERow.Row;
        myFile.Size=myFile.Size+strlen(ERow.Row) + 1;
        myFile.NumLines++;
        }
      else
        {
        fprintf(stderr, "ERow could not be found.\n");
        return 1;
        }
      }

    ERow.Salt = substring(ERow.Row, myFile.KeyStart+4, 0);
//    Scramble(URow.Key, ERow.Salt);
    asprintf(&ERow.Salt, "$%c$%s", myFile.HashMethod, ERow.Salt);
    PRow.ID = Hash(myFile.HashMethod, URow.Salt, ERow.Salt);
    }

  switch (Action)
  {
  case 1:
    //--passwdwrite
    {
    //We gaan een wachtwoord weg schrijven.
#if DEBUGLEVEL>0
    fprintf(stderr, "Writing password (Password=%s).\n", Password);
#endif    
    for (i=0 ; i<4 ; i++)
      {ERow.Key[i] = ERow.Row[i+myFile.KeyStart];}
#if DEBUGLEVEL>0
    fprintf(stderr, "Scrambling with key: %i, %i, %i, %i.\n", ERow.Key[0], ERow.Key[1], ERow.Key[2], ERow.Key[3]);
#endif    
    Scramble(ERow.Key, Password);
#if DEBUGLEVEL>0
    fprintf(stderr, "Encrypted password=%s.\n", Password);

    fprintf(stderr, "Calculating PRow (using PRowID %s, PW %s).\n", PRow.ID, Password);
#endif    
    PRow.Row = CalcPRow(PRow.ID, Password);

    myFile.Size = myFile.Size - RemoveRow(PRow.ID, &myFile);

    myFile.Rows[myFile.NumLines] = PRow.Row;
    myFile.Size = myFile.Size + strlen(PRow.Row) + 1;
    myFile.NumLines++;
    myFile.isDirty=1;

    break;
    }
  case 2:
    //--passwdread
  case 3:
    //--passwdcheck
    {
#if DEBUGLEVEL>0
    if (Action==2)
      {fprintf(stderr, "Searching for password.\n");}
    else
      {fprintf(stderr, "Checking for password.\n");}
#endif
    //We gaan een wachtwoord opzoeken.
    if (!PRow.ID)
      {
#if DEBUGLEVEL>0
      fprintf(stderr, "Entry not found...\n");
#endif
      return 4;
      }
#if DEBUGLEVEL>0
    fprintf(stderr, "Searching for PRow (PRowID=%s).\n", PRow.ID);
#endif
    SeekRow(&PRow, &myFile);
    if (PRow.Row)
      {
      tmp = substring(PRow.Row,myFile.KeyStart,0);
#if DEBUGLEVEL>0
      fprintf(stderr, "Encrypted password is: %s.\n", tmp);
#endif
      for (i=0 ; i<4 ; i++)
        {ERow.Key[i] = 0 - ERow.Row[i+myFile.KeyStart];}
#if DEBUGLEVEL>0
      fprintf(stderr, "Unscrambling with key: %i, %i, %i, %i.\n", ERow.Key[0], ERow.Key[1], ERow.Key[2], ERow.Key[3]);
#endif
      Scramble(ERow.Key, tmp);
      if (Action==2)
        {
        printf("%s\n", tmp);
        return 0;
        }
      else if (Password)
        {
        if (strcmp(Password, tmp)==0)
          {
          return 0;
          }
        else
          {
          return 5;
          }
        }
      else
        {
        return 0;
        }
      }
    else
      {
#if DEBUGLEVEL>0
      fprintf(stderr, "Password not found...\n");
#endif
      return 5;
      }
    break;
    }
  case 4:
    {
#if DEBUGLEVEL>0
    //--usergrant
    fprintf(stderr, "User grant...\n");
#endif
    URow.ID = Hash(myFile.HashMethod, defSalt, Login);
    GenKey(URow.Key);
    Scramble (URow.Key, URow.Salt);
    URow.Row = CalcRow(URow.ID, URow.Key, URow.Salt);
#if DEBUGLEVEL>0
    //--usergrant
    fprintf(stderr, "URow (for user %s) is %s.\n", Login, URow.Row);
#endif
    myFile.Rows[myFile.NumLines] = URow.Row;
    myFile.Size = myFile.Size + strlen(URow.Row) + 1;
#if DEBUGLEVEL>0
    fprintf(stderr, "URow added to contents.\n");
#endif
    myFile.NumLines++;
    myFile.isDirty=1;
    break;
    }
  case 5:
    {
#if DEBUGLEVEL>0
    //--userrevoke
    fprintf(stderr, "User revoke...\n");
#endif
    URow.ID = Hash(myFile.HashMethod, defSalt, Login);
    myFile.Size = myFile.Size - RemoveRow(URow.ID, &myFile);
    myFile.isDirty=1;
    break;
    }
  case 6:
    {
#if DEBUGLEVEL>0
    //--usercheck
    fprintf(stderr, "User check...\n");
#endif
    URow.ID = Hash(myFile.HashMethod, defSalt, Login);
    URow.Row = 0;
    SeekRow(&URow, &myFile);
    if (URow.Row)
      {return 0;}
    else
      {return 6;}
    break;
    }
  case 7:
    {
#if DEBUGLEVEL>0
    //--bulkload
    fprintf(stderr, "Bulkload...\n");
#endif
    if(stdin)
      {
      tmp = malloc(1024);
      while(fread(&tmp, 1024, ))

      }
    break;
    }
  }

  if (myFile.isDirty)
    {
#if DEBUGLEVEL>0
    fprintf(stderr, "Sorting array.\n");
#endif    
    //Array sorteren (alleen toegevoegde rijen) en naar file schrijven...
    for (i=myFile.NumOrgLines ; i<myFile.NumLines ; i++)
      {
fprintf(stderr, "Sorting line %i.\n", i);
      tmp = myFile.Rows[i];
      for (j=i-1 ; j>=0 ; j--)
        {
        if (strcmp(myFile.Rows[j], tmp) < 0)
          {
          break;
          }
        myFile.Rows[j+1] = myFile.Rows[j];
        }
      myFile.Rows[j+1] = tmp;
      }
#if DEBUGLEVEL>0
    fprintf(stderr, "Array looks like this:\n");
    for (i=0 ; i < myFile.NumLines ; i++)
      {fprintf(stderr, "Line %i: %s\n", i, myFile.Rows[i]);}
#endif

    myFile.Handle = gzopen(myFile.Name, "wb");

    if (myFile.Handle)
      {
#if DEBUGLEVEL>0
      fprintf(stderr, "Writing hash method (%c) to keyfile %s.\n", myFile.HashMethod, myFile.Name);
#endif
      gzputc(myFile.Handle, myFile.HashMethod);

#if DEBUGLEVEL>0
      fprintf(stderr, "Writing file size (%i) to keyfile %s.\n", myFile.Size, myFile.Name);
#endif    
      for (i=1 ; i<5 ; i++)
        {
#if DEBUGLEVEL>0
        fprintf(stderr, "Writing byte %i (%i) to keyfile %s.\n", i, myFile.Size % 256, myFile.Name);
#endif    
        gzputc(myFile.Handle, myFile.Size % 256);
        myFile.Size = myFile.Size / 256;
        }
#if DEBUGLEVEL>0
      fprintf(stderr, "Writing contents to keyfile %s.\n", myFile.Name);
#endif    
      for (i=0 ; i<myFile.NumLines ; i++)
        {
        j = strlen(myFile.Rows[i]);
        if (j>0)
          {
#if DEBUGLEVEL>0
          fprintf(stderr, "Writing line %i '%s' to keyfile %s.", i, myFile.Rows[i], myFile.Name);
#endif    
          ret = gzputs(myFile.Handle, myFile.Rows[i]);
          if (ret < 0) 
            {
#if DEBUGLEVEL>0
            fprintf(stderr, "NOK\n");
#endif
            }
          else
            {
            ret = gzputc(myFile.Handle, '\0');
            if (ret < 0)
              {
#if DEBUGLEVEL>0
              fprintf(stderr, "NOK\n");
#endif
              }
            else
              {
#if DEBUGLEVEL>0
              fprintf(stderr, "OK\n");
#endif
              }
            }
          }
        }

      gzclose(myFile.Handle);
      }
    }
  return 0;
  }
