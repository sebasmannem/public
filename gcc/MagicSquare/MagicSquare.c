#include <stdio.h>
#include <stdlib.h>

int Dimension, MaxNum, AvgSum;
//Structure of an elment
typedef struct {
   int    r;
   int    c;
   int    val;
} element;

int main(int argc, char *argv[])
{
  int c, r, i;
  if (argc < 2)
    {
    //Ask
    Dimension = 5;
    printf("Please specify dimension: ");
    scanf ("%i", &Dimension);
    }
  else
    {
    //Use argument
    Dimension = atoi(argv[1]);
    }
  //Number of elements in the Magic Square
  MaxNum = Dimension * Dimension ;

  //Average sum of rows (or columns)
  AvgSum = (MaxNum + 1) * MaxNum / Dimension / 2;

  //Build array with numbers
  int MagicSquare[Dimension][Dimension];
  element Elements[MaxNum];
  i = 0;
  for (r=1;r<=Dimension;r++)
    {
    for (c=1;c<=Dimension;c++)
      {
      i++;
      MagicSquare[r][c] = i;
      Elements[i].c = c;
      Elements[i].r = r;
      printf("Element(%i,%i)=%i\n", Elements[i].r, Elements[i].c, MagicSquare[r][c]);
      }
    }

  printf("Dimension: %i\n", Dimension);
  printf("MaxNum: %i\n", MaxNum);
  printf("RowSum: %i\n", AvgSum);
  return 0;
} 
