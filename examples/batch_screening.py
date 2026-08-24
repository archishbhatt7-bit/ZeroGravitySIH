"""ZeroGravity Batch Screening — screen an entire constellation.

This example demonstrates the class-based API for advanced workflows.
Requires a running ZeroGravity API instance or API key.
"""

from zerogravity import ZeroGravity

# Initialize with API key
og = ZeroGravity(api_key="og_live_your_key_here")

# Load your constellation's catalog
# catalog = og.load_catalog(operator="STARLINK")

# Screen against the full public catalog
# events = og.screen(catalog, threshold=1e-5)

# Filter critical events
# for event in events:
#     if event.probability and event.probability > 1e-4:
#         print(f"⚠️  CRITICAL: {event.primary_norad_id} vs {event.secondary_norad_id}")
#         print(f"   TCA: {event.tca}")
#         print(f"   Miss distance: {event.miss_distance_km:.2f} km")
#         print(f"   Pc: {event.probability:.2e}")

print("Batch screening will be available in ZeroGravity v0.2.")
print("Sign up at https://zerogravity.dev for early access.")
