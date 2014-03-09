#include <stdio.h>

int main()
{
  int i, i1, i2, i3;
  unsigned char c1[2];
  char c2[2];
  signed char c3[2];

//  for (i = 100; i < 150 ; i++)
//    {
    i = 129;
    c1[0] = 129;
    c1[1] = 0;
    c2[0] = 129;
    c2[1] = 0;
    c3[0] = 129;
    c3[1] = 0;

    c1[0] = c2[0];
    i1 = c1[0];
    i2 = c2[0];
    i3 = c3[0];
    printf("i=%i;c=%s;i1=%i;c2=%s;i2=%i,c3=%si3=%i\n", i, c1, i1, c2, i2, c3, i3);
//    }
  return 0;
}
