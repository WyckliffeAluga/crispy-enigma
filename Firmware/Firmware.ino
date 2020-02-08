
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
