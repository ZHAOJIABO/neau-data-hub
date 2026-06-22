CXX = g++
CXXFLAGS = -std=c++17 -Wall -O2 -I include

TARGET = canalsim
SOURCES = src/main.cpp src/Channel.cpp src/Solver.cpp src/ConfigIO.cpp src/Output.cpp

.PHONY: all clean run

all: $(TARGET)

$(TARGET): $(SOURCES)
	$(CXX) $(CXXFLAGS) -o $@ $^

clean:
	-rm -f $(TARGET)

run: $(TARGET)
	./$(TARGET)
