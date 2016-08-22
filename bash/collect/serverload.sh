#!/bin/bash
w | sed -n '/load average/{s/.*load average: //;s/,//g;p}'
