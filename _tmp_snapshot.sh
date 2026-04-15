set -e
cd /home/yuxiaoyu/rs_ontop_core
git restore --worktree --staged .
git checkout --orphan snapshot-main
git reset
git add -A
git commit -m "snapshot: initial import without history"
git branch -M master
git log -1 --oneline
git status --short
