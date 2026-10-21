a = get_objects_of_category(log_dir, category='REGULAR_VEHICLE')
a = turning(a, log_dir, direction='left')
b = get_objects_of_category(log_dir, category='VEHICLE')
b = stationary(b, log_dir)
b_gate = center_distance_gate(a, b, log_dir, max_center_dist=30)  # implicit 30 m centre-distance neighbour gate, identical in P and P'
out = scenario_and([in_same_lane(a, b, log_dir), b_gate])