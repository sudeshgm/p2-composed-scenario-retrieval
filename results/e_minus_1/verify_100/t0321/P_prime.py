a = get_objects_of_category(log_dir, category='REGULAR_VEHICLE')
a = has_velocity(a, log_dir, min_velocity=2)
b = get_objects_of_category(log_dir, category='VEHICLE')
b_gate = center_distance_gate(a, b, log_dir, max_center_dist=30)  # implicit 30 m centre-distance neighbour gate, identical in P and P'
out = scenario_and([near_objects(a, b, log_dir, distance_thresh=10), b_gate])