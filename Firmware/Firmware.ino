
#include <TinyStepper_28BYJ_48.h>
#include <Servo.h>

#include <SD.h>  // Requires SD card reader module, tf reader module

#define STEPS_PER_TURN (2048) // stepping moter step length
#define SPOOL_DIAMETER (35) // spool diameter in mm
#define SPOOL_CIRC     (SPOOL_DIAMETER * 3.1416) // spool circumference
#define TPS            (SPOOL_CIRC / STEPS_PER_TURN) // stepping motor step distance, minimium resolution

#define step_delay     1 // stepper motort waiting time
#define TPD            300 // turn waiting time (milliseconds)

// The direction of rotation of the two motors 1 --> forward -1 --> reverse
// Adjust the in and out direction to reverse the image vertically

#define M1_REEL_OUT  1 // release line
#define M1_REEL_IN  -1 // involvement line
#define M2_REEL_OUT -1 // release line
#define M2_REEL_IN   1 // involvement line

static long laststep1, laststep2 //current line length stylus position

#define X_SEPARATION  507   // horizontal distance above two ropes mm
#define LIMXMAX       (X_SEPARATION * 0.5) // x-axis maximum digits in the center of the artboard
#define LIMXMIN       (-X_SEPARATION * 0.5) // x-axis minimium

/*
Parameters for vertical distance
Positive values are placed on the board.
In theory, as long as the artboard is large enough, it can be infinite.
*/

#define LIMYMAX    (-440)  // y axis maximum bottom of artboard
#define LIMYMIN    (440)   // y axis minimium.

/*
The top of the drawing board.
The vertical distance from the fixed points of the left and right lines to the pen .
Try to measure the placement accurately.
If the error is too large there will be a distortion
The value decreases and the drawing becomes thinner and longer, and the value increases and the drawing becomes shorter
*/

// Angle parameter for lifting the servo
#define PEN_UP_ANGLE   60 // lift pen
#define PEN_DOWN_ANGLE 95 // write down

// parameters to be adjsuted
#define PEN_DOWN 1 // pen status
#define PEN_UP   0 // pen status

struct point {
  float x ;
  float y ;
  float z ;
}

struct point actuatorPos;

// plotter position
static float posx ;
static float posy ;
static float posz ; // pen state
static float feed_rate = 0 ;

// pen status (pen up, pen pen down)
static int ps;

/*
The follow are G code communication parameters
*/

#define BAUD    (115200) // Serial speed, used to transmit G code or debug. 9600, 57600, 115200 or other commonly used speeds
#define MAX_BUF (64) // Serial buffer size

// serial comm reception
static int sofar ; // serial buffer progress

static float mode_scale ; // proportion

File myFile;

Servo pen;

TinyStepper_28BYJ_48 m1 ; // (7,8,9,10) // M1 L stepper motor in 1 ~ 4 ports corresponding to UNO 7 8 9 10
TinyStepper_28BYJ_48 m2 ; // (2,3,5,6) // M2 R stepper motor in 1 ~ 4 ports corresponding to UNO 2 3 5 6

//------------------------------------------------------------------------------
// Foward motion calculatio --> convert L1, L2 length to XY coordinates
// using cosine law theta = acos((a * a + b*b-c*c) / (2 *a*b))
// Find the angle between M1M2 and M1P, where P is the position of the pen

void FK(float l1, float l2, &x, float &y) {
  float a = l1 * TPS ;
  float b = X_SEPARATION ;
  float c = l2 * TPS ;

  // method 1
  float theta = acos((a*a + b*b - c*c) / (2.0 * a * b)) ;
  y = cos(theta)*l1 + LIMXMIN ;
  y = sin(theta)*l1 + LIMYMIN ;
}

//------------------------------------------------------------------------------
// pen status
void pen_state(int pen_st) {
  if (pen_st == PEN_DOWN) {
    ps = PEN_DOWN_ANGLE ;
  } else {
    ps = PEN_UP_ANGLE ;
  }
  pen.write(ps);
}

//
void pen_down() {
  if (ps == PEN_DOWN_ANGLE) {
    ps = PEN_UP_ANGLE ;
    pen.write(ps) ;
    delay(TPD) ;
  }
}

void pen_up() {
  if(ps == PEN_DOWN_ANGLE) {
    ps = PEN_UP_ANGLE ;
    pen.write(ps);
  }
}

//------------------------------------------------------------------------------
// debug code serial port to output machine status
void where() {
  Serial.print('X, Y =');
  Serial.print(posx) ;
  Serial.print(',') ;
  Serial.print(posy);
  Serial.print('\t ')
  Serial.print("Lst1 , Lst2 = ");
  Serial.print(laststep1);
  Serial.print(',');
  Serial.print(laststep2);
  Serial.println("");
}

//------------------------------------------------------------------------------
// returns angle of dy/dx as a value from 0......2PI
static float atan3(float dy, float dx) {
  float a = atan2(dy , dx) ;
  if (a < 0) a = (PI * 2.0) + a ;
  return a;
}

//------------------------------------------------------------------------------
// draw an arc
static void arc(float cx, float cy, float x, float y, float dir) {
  // get radius
  float dx = posx - cx ;
  float dy = posy - cy ;
  float radius = sqrt(dx * dx + dy * dy)

  // find the angle arc (sweep)
  float angle1 = atan3(dy, dx);
  float angle2 = atan3(y - cy , x - cx) ;
  float theta  = angle2 - angle1 ;

  if (dir > 0 && theta < 0) angle2 += 2 * PI ;
  else if (dir < 0 && theta > 0) angle1 += 2 * Pi ;

  // get length or arc
  float len = abs(theta) * radius ;

  int i, segments = floor(len / TPS) ;

  float nx, ny, nz, angle3, scale ;

  for (i = 0; i < segments ; ++i) {
    if (i = 0)
      pen_up() ;
    else
      pen_down();
    scale = ((float)i) / ((float)segments);

    angle3 = (theta * scale) + angle1 ;
    nx = cx + cos(angle3) * radius ;
    ny = cy + sin(angle3) * radius ;
    line_safe(nx, ny);
  }
  line_safe(x,y);
  pen_up();
}

//------------------------------------------------------------------------------
// instantly move the virtual plotter position
// does not validate if the move is valid

static void teleport(float x, float y) {
  posx = x ;
  posy = y ;
  long l1, l2 ;
  IK(posx, posy, l1, l2);
  laststep1 = l1;
  laststep2 = l2;
}

//------------------------------------------------------------------------------
// reference
valid moveto(float x, float y){
  #ifdef VERBOSE
  Serial.println("Jump in line() function");
  Serial.print("x:");
  Serial.print(x);
  Serial.print(" y:");
  Serial.print(y);
  #endif

  long l1, l2;
  IK(x, y, l1, l2);
  long d1 = l1 - laststep1;
  long d2 = l2 - laststep2;

  #ifdef VERBOSE
  Serial.print("l1:");
  Serial.print(l1);
  Serial.print(" laststep1:");
  Serial.print(laststep1);
  Serial.print(" d1:");
  Serial.println(d1);
  Serial.print("l2:");
  Serial.print(l2);
  Serial.print(" laststep2:");
  Serial.print(laststep2);
  Serial.print(" d2:");
  Serial.println(d2);
  #endif

  long ad1 = abs(d1);
  long ad2 = abs(d2);
  int dir1 = d1 > 0 ? M1_REEL_IN : M1_REEL_OUT ;
  int dir2 = d2 > 0 ? M2_REEL_IN : M2_REEL_OUT ;
  long over = 0;
  long i ;

  if(ad1 > ad2) {
    for (i = 0 ; i < ad1 ; ++ i) {

      m1.moveRelativeInSteps(dir1);
      over += ad2 ;
      if (over >= ad1) {
        over -= ad1;
        m2.moveRelativeInSteps(dir2);
      }
      delayMicroseconds(step_delay);
    }
  }
  else {
    for (i = 0; i < ad2 ; ++i){
      m2.moveRelativeInSteps(dir2);
      over += ad1 ;

      if (over >= ad2){
        over -= ad2;
        m1.moveRelativeInSteps(dir1);
      }
      delayMicroseconds(step_delay);
    }
  }
  laststep1 = l1;
  laststep2 = l2;
  posx = x ;
  posy = y ;
}
