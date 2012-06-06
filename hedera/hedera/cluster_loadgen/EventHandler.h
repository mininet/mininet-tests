#ifndef EVENTHANDLER_H
#define EVENTHANDLER_H

class EventHandler {
    public:
        virtual int readHandler() = 0;
        virtual int writeHandler() = 0;
};

#endif
