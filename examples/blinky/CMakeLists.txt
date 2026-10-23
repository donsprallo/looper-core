# The example, built by CMake instead of by looper-cli.
#
# Both ways produce the same executable. This one is what a firmware project
# that already uses CMake would write: the simulation is a target among its
# others, and only what changed is recompiled.
#
#   cmake -S examples/blinky -B examples/blinky/build/cmake
#   cmake --build examples/blinky/build/cmake
#
# A project that does not want the Python tool in its build commits what
# looper-cli generate writes and configures with -DLOOPER_GENERATE=OFF.
cmake_minimum_required(VERSION 3.20)
project(blinkySimulation C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# A project of its own would fetch looper-rt here with FetchContent. These
# examples use the neighbouring checkout instead, so that a change to the
# runtime is built and tested without publishing it first. Point
# LOOPER_RT_ROOT somewhere else to build against another copy.
set(LOOPER_RT_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../looper-rt"
    CACHE PATH "Where the looper runtime is checked out")
if(NOT EXISTS "${LOOPER_RT_ROOT}/CMakeLists.txt")
    message(FATAL_ERROR
        "No looper runtime at '${LOOPER_RT_ROOT}'. Check out looper-rt beside "
        "this repository, or pass -DLOOPER_RT_ROOT=<path>.")
endif()
add_subdirectory(${LOOPER_RT_ROOT} looper_rt)

# The sources are named here rather than taken from the definition, which is
# what a project whose CMake already knows its firmware would do. A project
# with dozens of source directories does the other thing and lists nothing,
# letting the generator hand CMake what the definition already says; see
# "Letting the definition name the sources" in docs/building.md.
looper_add_simulation(blinky
    DEFINITION ${CMAKE_CURRENT_LIST_DIR}/looper.toml
    GENERATED ${CMAKE_CURRENT_LIST_DIR}/build/generated
    SOURCES
        ${CMAKE_CURRENT_LIST_DIR}/src/main.c
        ${CMAKE_CURRENT_LIST_DIR}/src/app.c
        ${CMAKE_CURRENT_LIST_DIR}/src/device_model.c
)
