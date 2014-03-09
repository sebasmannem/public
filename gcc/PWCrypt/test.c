#include <stdio.h>

int main()
{
  int i, i1;
  char c1;

  for (i = 32; i < 127 ; i++)
    {
    c1 = i;

    i1 = c1;
    printf("i=%i;c=%c;i1=%i\n", i, c1, i1);
    }
  return 0;
}
