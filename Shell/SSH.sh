#!/usr/bin/expect

#Usage sshsudologin.expect

set timeout 60

spawn ssh [lindex $argv 1]@[lindex $argv 0]

expect "yes/no" {
send "yes\r"
expect "*?assword" { send "[lindex $argv 2]\r" }
} "*?assword" { send "[lindex $argv 2]\r" }

expect "# " { send "su - [lindex $argv 3]\r" }
expect ": " { send "[lindex $argv 4]\r" }
expect "# " { send "ls -ltr\r" }
interact