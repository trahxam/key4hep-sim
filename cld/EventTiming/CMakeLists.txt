cmake_minimum_required(VERSION 3.16)
project(EventTiming)

find_package(Gaudi REQUIRED)
find_package(ROOT REQUIRED COMPONENTS Core RIO Tree)

gaudi_add_module(EventTimingPlugins
    SOURCES src/EventTiming.cpp
    LINK
        Gaudi::GaudiKernel
        ROOT::Core
        ROOT::RIO
        ROOT::Tree
)
