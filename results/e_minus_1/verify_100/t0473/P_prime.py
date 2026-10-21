a = get_objects_of_category(log_dir, category='REGULAR_VEHICLE')
a = accelerating(a, log_dir, min_accel=1.0)
b = get_objects_of_category(log_dir, category='REGULAR_VEHICLE')
b_gate = center_distance_gate(a, b, log_dir, max_center_dist=30)  # implicit 30 m centre-distance neighbour gate, identical in P and P'
out = scenario_and([has_objects_in_relative_direction(a, b, log_dir, direction='left', within_distance=15), b_gate])