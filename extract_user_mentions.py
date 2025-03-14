
import json

# Load ticket stats
with open('ticket_stats.json', 'r') as f:
    ticket_stats = json.load(f)

# Format user IDs as mentions and calculate averages
for user_id, stats in ticket_stats.items():
    mention = f"<@{user_id}>"
    
    # Get message stats if available, or set to 0
    messages_sent = stats.get('messages_sent', 0)
    
    # Calculate averages
    tickets_participated = stats.get('tickets_participated', 0)
    tickets_claimed = stats.get('tickets_claimed', 0)
    tickets_closed = stats.get('tickets_closed', 0)
    
    # Avoid division by zero
    avg_msgs_per_participation = messages_sent / tickets_participated if tickets_participated > 0 else 0
    total_tickets = tickets_claimed + tickets_closed
    avg_msgs_per_ticket = messages_sent / total_tickets if total_tickets > 0 else 0
    
    print(f"User ID: {user_id} → Mention format: {mention}")
    print(f"  Messages sent: {messages_sent}")
    print(f"  Avg msgs per participation: {avg_msgs_per_participation:.2f}")
    print(f"  Avg msgs per ticket: {avg_msgs_per_ticket:.2f}")
    print("---")

# Example of how to use these mentions in other code
print("\nExample usage in code:")
print("await ctx.send(f\"Stats for {mention}: {avg_msgs_per_participation:.2f} msgs per participation\")")
