cmake_minimum_required(VERSION 3.16)
project(CanalSim CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# MSVC 时使用多线程
if(MSVC)
    add_compile_options(/W4 /permissive-)
else()
    add_compile_options(-Wall -Wextra -pedantic)
endif()

set(SOURCES
    src/main.cpp
    src/Channel.cpp
    src/Solver.cpp
    src/ConfigIO.cpp
    src/Output.cpp
)

add_executable(canalsim ${SOURCES})

# 自动在输出目录生成结果文件
set_target_properties(canalsim PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}
)

install(TARGETS canalsim DESTINATION bin)
