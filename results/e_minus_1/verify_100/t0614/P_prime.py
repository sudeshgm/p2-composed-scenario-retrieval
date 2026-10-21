a = get_objects_of_category(log_dir, category='REGULAR_VEHICLE')
a = has_velocity(a, log_dir, min_velocity=2)
a = changing_lanes(a, log_dir)
b = scenario_or([get_objects_of_category(log_dir, category='BUS'), get_objects_of_category(log_dir, category='SCHOOL_BUS'), get_objects_of_category(log_dir, category='ARTICULATED_BUS')])
b_gate = center_distance_gate(a, b, log_dir, max_center_dist=30)  # implicit 30 m centre-distance neighbour gate, identical in P and P'
out = scenario_and([has_objects_in_relative_direction(a, b, log_dir, direction='forward', within_distance=25), b_gate])