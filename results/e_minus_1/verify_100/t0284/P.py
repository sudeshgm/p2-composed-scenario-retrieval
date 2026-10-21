a = get_objects_of_category(log_dir, category='EGO_VEHICLE')
a = has_velocity(a, log_dir, min_velocity=2)
b = scenario_or([get_objects_of_category(log_dir, category='BUS'), get_objects_of_category(log_dir, category='SCHOOL_BUS'), get_objects_of_category(log_dir, category='ARTICULATED_BUS')])
b_gate = center_distance_gate(a, b, log_dir, max_center_dist=30)  # implicit 30 m centre-distance neighbour gate, identical in P and P'
out = scenario_and([facing_toward(a, b, log_dir, max_distance=30), b_gate])