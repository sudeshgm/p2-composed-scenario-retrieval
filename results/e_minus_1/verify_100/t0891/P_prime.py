a = get_objects_of_category(log_dir, category='EGO_VEHICLE')
a = has_velocity(a, log_dir, min_velocity=2)
b = scenario_or([get_objects_of_category(log_dir, category='BOX_TRUCK'), get_objects_of_category(log_dir, category='TRUCK'), get_objects_of_category(log_dir, category='TRUCK_CAB')])
b = stationary(b, log_dir)
b_gate = center_distance_gate(a, b, log_dir, max_center_dist=30)  # implicit 30 m centre-distance neighbour gate, identical in P and P'
out = scenario_and([near_objects(a, b, log_dir, distance_thresh=10), b_gate])