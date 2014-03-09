#define _GNU_SOURCE         /* See feature_test_macros(7) */
#include <stdio.h>
//int asprintf(char **strp, const char *fmt, ...);
//int fprintf(FILE *stream, const char *format, ...);
//int fscanf(FILE *stream, const char *format, ...);
//int printf(const char *format, ...);
//int puts(const char *s);
//size_t fread(void *ptr, size_t size, size_t nmemb, FILE *stream);

#include <unistd.h>
//char *crypt(const char *key, const char *salt);
//int gethostname(char *name, size_t namelen);

#include <stdlib.h>
//int rand(void);
//void srand(unsigned int seed);
//void *myMalloc(size_t size);
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

#define DEBUGLEVEL 0

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

void *myMalloc(size_t size)
  {
  void *tmp;
  tmp=malloc(size);
  if (!tmp)
    {
    fprintf(stderr, "Malloc error. Probably not enough memory.\n");
    exit(1);
    }
#if DEBUGLEVEL>2
  else
    {
    fprintf(stderr, "Malloc success.\n");
    }
#endif
  return tmp;

  }

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

  tmp=(char *) myMalloc (length+1);
  for (i=0 ; i < length ; i++)
    {tmp[i] = string[start + i];}
  tmp[length]= '\0';

  return tmp;
  }

char *ValidCharacters()
  {
  static char *Tmp=0;
  int i;
#if DEBUGLEVEL>1
  fprintf(stderr, "In ValidCharacters.\n");
#endif
  if (!Tmp)
    {
    Tmp = myMalloc(65);
    // ValidCharacters bevat alle hoofdletter, kleine letters, getallen '.' en '/'.
    // Dit wordt gebruikt voor het genereren van bijvoorbeeld een Salt.
    for (i=0 ; i<62; i++)
      {
      if (i<10)
        {Tmp[i] = i+48;} //0-9
      else if (i < 36)
        {Tmp[i] = i+55;} //A-Z
      else
        {Tmp[i] = i+61;} //a-z
      }
    Tmp[62] = '.';
    Tmp[63] = '/';
    Tmp[64] = '\0';
    }
#if DEBUGLEVEL>1
  fprintf(stderr, "End of ValidCharacters.\n");
#endif
  return Tmp;
  }

char *RndString(int length)
  {
  int i,val;
  char *ValidChars, *tmp;

#if DEBUGLEVEL>1
  fprintf(stderr, "In RndString.\n");
#endif

  ValidChars=ValidCharacters();
#if DEBUGLEVEL>1
  fprintf(stderr, "ValidChars=%s\n", ValidChars);
#endif

  static unsigned int offset = 0;
  tmp = (char *) myMalloc (length + 1);
 
  //Seed number for rand()
  srand((unsigned int) offset + time(0) + getpid());
  offset+=2;

#if DEBUGLEVEL>1
  fprintf(stderr, "Filling tmp.\n");
#endif
 
  //ASCII characters 33 to 126
  for (i=0 ; i< length; i++)
    {
    val = rand() % strlen(ValidChars);
    tmp[i] = ValidChars[val];
    srand(rand());
    }

#if DEBUGLEVEL>1
  fprintf(stderr, "Ending tmp.\n");
#endif

  tmp[length] = '\0';

//  free(ValidChars);
#if DEBUGLEVEL>1
  fprintf(stderr, "End of RndString.\n");
#endif

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
    case '0': return 11; //DES
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
    Salt2=(char *) myMalloc(21);
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
    {Ret = substring(Hashed,2,0);}
  RetLen = strlen(Ret);
  if (RetLen != HashLen)
    {
#if DEBUGLEVEL>1
      fprintf(stderr, "Length of hash (%i) is other the expected (%i)\n", RetLen, HashLen);
#endif
    }

  if (Method != '0')
    {free(Salt2);}
  return Ret;
  }

void RemoveRow(char *RowID, struct keyFile *myFile)
  {
  int i, LenRowID, Cmp;
  char *tmp;
  LenRowID=strlen(RowID);
#if DEBUGLEVEL>1
  fprintf(stderr, "Removing Row with RowID=%s.\n", RowID);
#endif    
  for (i=0 ; i<myFile->NumLines ; i++)
    {
#if DEBUGLEVEL>1
    fprintf(stderr, "%i:", i);
#endif    
    tmp = substring(myFile->Rows[i], 0, LenRowID);
    Cmp = strcmp(tmp, RowID);
//    free(tmp);
#if DEBUGLEVEL>1
    fprintf(stderr, "%s", tmp);
#endif    
    if (Cmp == 0)
      {
      myFile->Size -= strlen(myFile->Rows[i]) + 1;
      myFile->Rows[i] = "";
      myFile->isDirty=1;
#if DEBUGLEVEL>1
      fprintf(stderr, "=DELETED\n");
#endif    
      break;
      }
    else
      {
#if DEBUGLEVEL>1
      fprintf(stderr, "=NOK\n");
#endif    
      }
    }
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

void CalcRow(struct Row *myRow)
  {
  int i;
#if DEBUGLEVEL>1
  fprintf(stderr, "In CalcRow.\n");
#endif

  if (!myRow->ID)
    {
    fprintf(stderr, "myRow is Invalid. myRow.ID is missing.\n");
    exit(1);
    }
  else if (myRow->Row)
    {
    //myRow->Row klopt al. We hoeven hier niets te doen.
#if DEBUGLEVEL>1
    fprintf(stderr, "myRow->Row allready calculated.\n");
#endif
    }
  else if (myRow->Value)
    {
#if DEBUGLEVEL>1
    fprintf(stderr, "Using myRow->Value\n");
#endif
    myRow->Row = (char *) myMalloc(strlen(myRow->ID) + strlen(myRow->Value) + 1);
    asprintf(&myRow->Row, "%s%s", myRow->ID, myRow->Value);
    }
  else if (myRow->Salt)
    {
#if DEBUGLEVEL>1 
    fprintf(stderr, "Using myRow->Salt\n");
#endif
    myRow->Row = (char *) myMalloc(strlen(myRow->ID) + strlen(myRow->Salt) +5);
    asprintf(&myRow->Row, "%s%c%c%c%c%s", myRow->ID, myRow->Key[0], myRow->Key[1], myRow->Key[2], myRow->Key[3], myRow->Salt);
    }
  else
    {
#if DEBUGLEVEL>1 
    fprintf(stderr, "Missing myRow.Value and myRow.Salt Cannot compute myRow->Row.\n");
#endif
    exit(1);
    }

#if DEBUGLEVEL>1
  fprintf(stderr, "myRow->Row is:%s\nSetting myRow->Value\n", myRow->Row);
#endif
//  if (myRow->Value)
//    {free(myRow->Value);}
  myRow->Value = myRow->Row + strlen(myRow->ID);
#if DEBUGLEVEL>1
  fprintf(stderr, "myRow->Value set\n");
#endif

  if (myRow->Salt)
    {free(myRow->Salt);}
  if (strlen(myRow->Value) == 20)
    {
    myRow->Salt = substring(myRow->Value, 4, 0);
#if DEBUGLEVEL>1
  fprintf(stderr, "myRow->Salt set\n");
#endif

    for (i=0 ; i<4 ; i++)
      {myRow->Key[i] = myRow->Value[i];}
#if DEBUGLEVEL>1
  fprintf(stderr, "myRow->Key set\n");
#endif
    }
  else
    {
    myRow->Salt = 0;
#if DEBUGLEVEL>1
  fprintf(stderr, "myRow->Salt unset\n");
#endif

    }
  }

void SeekRow(struct Row *myRow, struct keyFile *myFile)
  {
  int i, LenRowID;
  char *tmp;
#if DEBUGLEVEL>1
  fprintf(stderr, "In SeekRow.\n");
#endif
  LenRowID=strlen(myRow->ID);
#if DEBUGLEVEL>1
  fprintf(stderr, "Searching for Row with RowID=%s.\n", myRow->ID);
#endif
  for (i=0 ; i<myFile->NumLines ; i++)
    {
#if DEBUGLEVEL>1
    fprintf(stderr, "%i:", i);
#endif
    tmp = substring(myFile->Rows[i], 0, LenRowID);
#if DEBUGLEVEL>1
    fprintf(stderr, "%s", tmp);
#endif
    if (strcmp(tmp, myRow->ID) == 0)
      {
      myRow->Row = myFile->Rows[i];
      CalcRow(myRow);
#if DEBUGLEVEL>1
      fprintf(stderr, "=OK\nRowValue=%s.\n", myRow->Value);
#endif
      break;
      }
    else
      {
#if DEBUGLEVEL>1
      fprintf(stderr, "=NOK\n");
#endif
      }
    }
  free(tmp);
#if DEBUGLEVEL>1
  fprintf(stderr, "End of SeekRow.\n");
#endif
  }

void GenRow(struct Row *myRow)
  {
#if DEBUGLEVEL>1
  fprintf(stderr, "In GenRow.\n");
#endif

  if (myRow->Value)
    {
    myRow->Value=0;
#if DEBUGLEVEL>1
    fprintf(stderr, "myRow->Value=0.\n");
#endif
    }
  if (myRow->Row)
    {
    free(myRow->Row);
    myRow->Row=0;
#if DEBUGLEVEL>1
    fprintf(stderr, "free(myRow->Row).\n");
#endif
    }
//  myRow->Row = (char *) myMalloc(strlen(myRow->ID) + 17);
  GenKey(myRow->Key);
#if DEBUGLEVEL>1
    fprintf(stderr, "GenKey(myRow->Key).\n");
#endif

  myRow->Salt = RndString(16);
#if DEBUGLEVEL>1
    fprintf(stderr, "myRow->Salt = RndString(16).\n");
#endif
  
  CalcRow(myRow);
#if DEBUGLEVEL>1
  fprintf(stderr, "End of GenRow.\n");
#endif
  }

void AddReplaceRow(struct Row *myRow, struct keyFile *myFile)
  {
  if (!myRow->ID)
    {
#if DEBUGLEVEL>1
    fprintf(stderr, "Error: AddReplaceRow started without valid myRow->ID!!!\n");
#endif
    exit(1);
    }

  RemoveRow(myRow->ID, myFile);
  CalcRow(myRow);

  //myRow->Row moet toegevoegd worden aan myFile.
  myFile->Rows[myFile->NumLines] = myRow->Row;
  myFile->Size = myFile->Size + strlen(myRow->Row) + 1;
  myFile->NumLines++;
  myFile->isDirty=1;
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

  printf("Bulk load:\n");
  printf("-> Load bulk of data to file: echo 'Login=Password\\nlogin2=AnotherPW' | %s --bulkload --file [path to file].\n", App);
  printf("   Every pair consists of a Entry (login) and a Password. They should be divided by a equal sign (=).\n");
  printf("   Every pair should be on another line (divided by Newline \\n).\n");
  printf("   Every line should be less than 1024 characters (restruction of bulkload only).\n\n");

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
  int i, j, val, ret, Action = 0;
  char *UserName = 0, *Entry = 0, *Password = 0, *Login = 0;
  char *defSalt = 0;
  char *tmp = 0;
  char *ValidChars;
  ValidChars = ValidCharacters();


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

    myFile.Contents=myMalloc(myFile.Size+1);
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
    myFile.Rows = myMalloc(i);
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

    myFile.Rows=myMalloc(3 * sizeof(char*));
    
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
    defSalt = (char *) myMalloc(21);
    defSalt[0] = '$';
    defSalt[1] = myFile.HashMethod;
    defSalt[2] = '$';
    for (i=0 ; i<16 ; i++)
      {
      val = (i * 11) % strlen(ValidChars);
      defSalt[i + 3] = ValidChars[val];
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
    fprintf(stderr, "URow=%s (found).\n", URow.Row);
#endif    
    }
  else
    {
#if DEBUGLEVEL>0
    fprintf(stderr, "Generating URow.\n");
#endif    
    GenRow(&URow);
//    Scramble (URow.Key, URow.Salt);

#if DEBUGLEVEL>0
    fprintf(stderr, "URow=%s (generated).\n", URow.Row);
#endif
    AddReplaceRow(&URow, &myFile);
#if DEBUGLEVEL>0
    fprintf(stderr, "URow added to contents.\n");
#endif    
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
        GenRow(&ERow);
#if DEBUGLEVEL>0
        fprintf(stderr, "ERow=%s (calculated).\n", ERow.Row);
#endif
        AddReplaceRow(&ERow, &myFile);
        }
      else
        {
#if DEBUGLEVEL>0
        fprintf(stderr, "ERow could not be found.\n");
#endif
        return 1;
        }
      }

//    Scramble(URow.Key, ERow.Salt);
//    asprintf(&ERow.Salt, "$%c$%s", myFile.HashMethod, ERow.Salt);
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
    if (PRow.Row)
      {free(PRow.Row);}
    PRow.Row=0;
    PRow.Value=Password;
    CalcRow(&PRow);

#if DEBUGLEVEL>0
    fprintf(stderr, "PRow=%s (calculated).\n", PRow.Row);
#endif
    AddReplaceRow(&PRow, &myFile);
    break;
    }
  case 2:
  case 3:
    //--passwdread (Action=2)
    //--passwdcheck (Action=3)
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
    URow.Row=0;
    URow.Value=0;
    CalcRow(&URow);
#if DEBUGLEVEL>0
    //--usergrant
    fprintf(stderr, "URow (for user %s) is %s.\n", Login, URow.Row);
#endif

    AddReplaceRow(&URow, &myFile);
#if DEBUGLEVEL>0
    fprintf(stderr, "URow added to contents.\n");
#endif
    break;
    }
  case 5:
    {
#if DEBUGLEVEL>0
    //--userrevoke
    fprintf(stderr, "User revoke...\n");
#endif
    URow.ID = Hash(myFile.HashMethod, defSalt, Login);
    RemoveRow(URow.ID, &myFile);
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
      clearerr(stdin);
      Entry = myMalloc(1025);
      do
        {
        Entry[0] = '\0';

#if DEBUGLEVEL>0
      //--bulkload
      fprintf(stderr, "Read new line...\n");
#endif

      tmp = fgets(Entry, 1025, stdin);
        if (ferror(stdin))
          {
          fprintf(stderr, "Error %i has occurred. Data was not written out.\n", ferror(stdin));
          exit(1);
          }

        Password=0;
        for (i=0 ; i<=1025 ; i++)
          {
          if (Entry[i] == '\n' || Entry[i] == '\0')
            {
            Entry[i] = '\0';
            break;
            }
          else if (Entry[i] == '=')
            {
            Password=Entry + i + 1;
            Entry[i] = '\0';
//            break;
            }
          else if (i == 1025)
            {
            fprintf(stderr, "One Item (Entry=Password pair) is too large (%i is larger than 1024 characters).\n", i);
            fprintf(stderr, "Please add this Entry by hand and retry without this Entry.\nData will not be written out.\n");
            exit(1);
            }
          }

        if (Entry[0])
          {
#if DEBUGLEVEL>0
          fprintf(stderr, "Removing row for %s\n", Entry);
#endif

          ERow.ID = Hash(myFile.HashMethod, URow.Salt, Entry);
          ERow.Row = 0;
          SeekRow(&ERow, &myFile);
          if (ERow.Row)
            {
            PRow.ID = Hash(myFile.HashMethod, URow.Salt, ERow.Salt);
#if DEBUGLEVEL>0
          fprintf(stderr, "Removing PRow with ID %s\n", PRow.ID);
#endif
            RemoveRow(PRow.ID, &myFile);
            }
          if (Password)
            {
#if DEBUGLEVEL>0
            fprintf(stderr, "Writing entry -> Item = %s -> Password = %s\n", Entry, Password);
#endif

            GenRow(&ERow);
            PRow.ID = Hash(myFile.HashMethod, URow.Salt, ERow.Salt);
            PRow.Row=0;
            PRow.Value=Password;
            Scramble(ERow.Key, PRow.Value);
            CalcRow(&PRow);
#if DEBUGLEVEL>0
            fprintf(stderr, "Writing ERow (ID = %s)\nWriting PRow (ID = %s)\n", ERow.Row, PRow.Row);
#endif
            AddReplaceRow(&ERow, &myFile);
            AddReplaceRow(&PRow, &myFile);
            }
          else
            {
#if DEBUGLEVEL>0
            fprintf(stderr, "Removing ERow with ID %s\n", PRow.ID);
#endif
            RemoveRow(ERow.ID, &myFile);
            }
          }
        }
      while(!feof(stdin));
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
#if DEBUGLEVEL>0
      fprintf(stderr, "Sorting line %i.\n", i);
#endif
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
