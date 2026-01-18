#!/bin/bash
# Claude Code Hook: Auto-checkout develop branch
# This hook runs when the user submits a prompt in Claude Code

# Get the current branch
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)

# Check if we're in a git repository
if [ $? -ne 0 ]; then
    echo "Not in a git repository"
    exit 0
fi

# If not on develop branch, switch to it
if [ "$CURRENT_BRANCH" != "develop" ]; then
    echo "🔄 Switching to develop branch..."
    git checkout develop 2>/dev/null

    if [ $? -eq 0 ]; then
        echo "✅ Checked out develop branch"
        echo "📝 Ready for development!"
    else
        echo "⚠️  Could not switch to develop branch"
        echo "   Current branch: $CURRENT_BRANCH"
    fi
else
    echo "✅ Already on develop branch"
fi

exit 0
