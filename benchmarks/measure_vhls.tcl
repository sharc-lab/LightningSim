if { $argc != 2 } {
    puts stderr "Usage: $argv0 <solution directory> <output file>"
    exit 1
}

set solution_dir [lindex $argv 0]
set output_file [lindex $argv 1]
set solution_name [file tail $solution_dir]
set project_dir [file dirname $solution_dir]
set project_name [file tail $project_dir]
set project_parent_dir [file dirname $project_dir]
set fp [open $output_file "w"]
cd $project_parent_dir
open_project $project_name
file delete -force [file join $solution_dir ".autopilot"]
open_solution $solution_name
set start_time [clock milliseconds]
csynth_design
set end_time [clock milliseconds]
puts $fp "HLS start ms,$start_time"
puts $fp "HLS end ms,$end_time"
set start_time [clock milliseconds]
catch { cosim_design }
set end_time [clock milliseconds]
puts $fp "Cosim start ms,$start_time"
puts $fp "Cosim end ms,$end_time"
close $fp
exit
