
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
