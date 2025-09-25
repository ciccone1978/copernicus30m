# Git Workflow: Saving In-Progress Work to a Feature Branch

This guide outlines the standard process for taking uncommitted work from your main branch and safely moving it to a new, dedicated "feature branch" for future development. This is useful when you start a feature but decide not to merge it immediately.

## The Scenario

You are on your `main` branch and have made several changes to implement a new feature (e.g., "interactive list highlighting"). You want to revert your `main` branch to its last clean state but save this new feature's code to work on later.

---

### Step 1: Check the Status of Your Work

Always begin by seeing which files you've modified. This ensures you know what you're about to save.

```bash
git status
```
This will show you a list of "Changes not staged for commit".

### Step 2: Stash Your Changes
A "stash" is a temporary holding area (a shelf) for your uncommitted changes. This command cleans your working directory, reverting it to the last commit, while keeping your work safe.

```bash
# The '-m' flag adds a descriptive message so you can identify the stash later.
git stash push -m "Feature: Interactive highlight on list select"
```
After running this, git status will show a "clean" working directory. Your changes are now safely stored. You can view all your stashes with git stash list.

### Step 3: Create the New Feature Branch
Create a new branch that will permanently store this feature. This new branch will be an exact copy of your main branch at its current commit.

```bash
# This creates the branch but does not switch to it yet.
git branch highlight-feature
```

### Step 4: Switch to the New Branch
Move your current working session from the main branch to the new feature branch.

```bash
git switch highlight-feature
```
Your terminal prompt will likely change to show you are on (highlight-feature).

### Step 5: Apply Your Stashed Work
Now that you are on the new branch, take your saved work from the stash and apply it here.

```bash
# 'pop' applies the most recent stash and removes it from the stash list.
git stash pop
```

If you run git status again, you will see your modified files have reappeared. You are now on the new branch with your feature's code restored.

### Step 6: Commit the Feature to its Branch
Make the changes a permanent part of this new branch's history by committing them.

```bash
# Stage all the changed files for the commit
git add .

# Commit the changes with a clear message
git commit -m "feat: Implement active highlight on list selection"
```
Your feature is now safely and permanently stored on the highlight-feature branch.

## Daily Workflow Summary
Once this is set up, your daily workflow becomes very simple and powerful.

### To Work on the Main Project
```bash
# Switch back to your main, stable branch
git switch main
```
You can now work on other features, fix bugs, and make commits here without affecting the highlight-feature.

### To Resume Work on the Saved Feature
```bash
# Switch to the feature branch
git switch highlight-feature
```
You will find the code exactly as you committed it, ready for you to continue your work.

### To Merge the Feature into Main (When Ready)
When the feature is complete and you want to add it to your main application:
```bash
# 1. Go to the branch you want to merge INTO
git switch main

# 2. Merge the feature branch's changes INTO main
git merge highlight-feature
```
Your main branch now contains all the code from the feature branch.