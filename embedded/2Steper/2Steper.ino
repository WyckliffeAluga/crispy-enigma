#include <AccelStepper.h>

#define FULLSTEP 4
#define HALFSTEP 8

// Wiring method
// Motor 1 connection
#define motorPin1  2     //  28BYJ48 pin 1 Connect to port 2 of arduino
#define motorPin2  3     //  28BYJ48 pin 2 Pick up 3 
#define motorPin3  5     //  28BYJ48 pin 3 Connect 5  Note that 4 port reserves SD card reader
#define motorPin4  6     //  28BYJ48 pin 4 Pick up 6 

//电机2的接法
#define motorPin5  7     //  28BYJ48 pin 1 Pick up 7
#define motorPin6  8     //  28BYJ48 pin 2 Pick up 8
#define motorPin7  9     //  28BYJ48 pin 3 Pick up 9
#define motorPin8  10    //  28BYJ48 pin 4 PIck up 10


AccelStepper stepper1(HALFSTEP, motorPin1, motorPin3, motorPin2, motorPin4);
AccelStepper stepper2(HALFSTEP, motorPin5, motorPin7, motorPin6, motorPin8);

void setup() 
{
  Serial.begin(9600);
  stepper1.setMaxSpeed(1000.0);     //Maximum speed, excessively high torque becomes small, and it is easy to lose step if it exceeds 256
  stepper1.setAcceleration(256.0);  //Acceleration and test stabilization procedures can be adjusted.
  stepper1.setSpeed(256);           //Speed
  //Depending on FULLSTEP or HALFSTEP, 1024 or 512 stepper motors make one revolution  
  //Set the number of rotation steps for motor 1. Adjustable (the larger the number, the larger the graphic size)
  stepper1.moveTo(790);
  
  stepper2.setMaxSpeed(1000.0);
  stepper2.setAcceleration(256.0);
  stepper2.setSpeed(256);
  //同stepper1
  stepper2.moveTo(1226);  
  
}
void loop()  
{
  if(stepper1.distanceToGo() == 0)
    stepper1.moveTo(-stepper1.currentPosition());
  if(stepper2.distanceToGo() == 0)
    stepper2.moveTo(-stepper2.currentPosition());
    
  stepper1.run();
  stepper2.run();
    
}
