import bcrypt

password = "adminpassword"
print(f"Original password: {password}")

# Hash the password
hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print(f"Hashed password: {hashed_password.decode('utf-8')}")

# Verify the password
is_valid = bcrypt.checkpw(password.encode('utf-8'), hashed_password)
print(f"Is password valid? {is_valid}")

# Test with a wrong password
wrong_password = "wrongpassword"
is_wrong_valid = bcrypt.checkpw(wrong_password.encode('utf-8'), hashed_password)
print(f"Is wrong password valid? {is_wrong_valid}")

# Test verification with a stored hash (simulating database retrieval)
stored_hash_from_db = hashed_password.decode('utf-8') # Simulate what's stored in DB
print(f"Simulated DB hash: {stored_hash_from_db}")
is_valid_from_db = bcrypt.checkpw(password.encode('utf-8'), stored_hash_from_db.encode('utf-8'))
print(f"Is password valid from simulated DB? {is_valid_from_db}")