#!/bin/bash
#
# Setup a memorable local hostname for the Activity Tracker
#
# This adds an entry to /etc/hosts so you can access the dashboard
# at http://tracker.local instead of http://127.0.0.1:5050
#

HOSTNAME="tracker.local"
HOSTS_ENTRY="127.0.0.1 $HOSTNAME"

echo "=============================================="
echo "  Activity Tracker - Custom URL Setup"
echo "=============================================="
echo
echo "This will add '$HOSTNAME' to your hosts file"
echo "so you can access the dashboard at:"
echo
echo "  http://$HOSTNAME:5050"
echo

# Check if already exists
if grep -q "$HOSTNAME" /etc/hosts 2>/dev/null; then
    echo "✓ '$HOSTNAME' is already configured!"
    echo
    exit 0
fi

echo "This requires administrator privileges."
echo

# Add to hosts file
sudo bash -c "echo '$HOSTS_ENTRY' >> /etc/hosts"

if [ $? -eq 0 ]; then
    echo "✓ Successfully added '$HOSTNAME' to /etc/hosts"
    echo
    echo "You can now access the dashboard at:"
    echo "  http://$HOSTNAME:5050"
    echo
    echo "To remove this later, edit /etc/hosts and remove the line:"
    echo "  $HOSTS_ENTRY"
else
    echo "✗ Failed to update /etc/hosts"
    exit 1
fi
