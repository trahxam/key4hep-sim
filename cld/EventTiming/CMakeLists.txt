cmake_minimum_required(VERSION 3.16)
project(EventTiming)

find_package(Gaudi REQUIRED)
find_package(k4FWCore REQUIRED)
find_package(podio REQUIRED)

gaudi_add_module(EventTimingPlugins
    SOURCES src/EventTiming.cpp
    LINK
        Gaudi::GaudiKernel
        k4FWCore::k4FWCore
)
