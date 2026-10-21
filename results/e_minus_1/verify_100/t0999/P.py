a = scenario_or([get_objects_of_category(log_dir, category='BUS'), get_objects_of_category(log_dir, category='SCHOOL_BUS'), get_objects_of_category(log_dir, category='ARTICULATED_BUS')])
a = has_velocity(a, log_dir, min_velocity=2)
out = a