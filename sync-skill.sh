#!/bin/bash
# 同步 hub-client skill 到所有 subagent 工作空间

set -e

# 源目录
SOURCE="$HOME/.openclaw/workspace/Claw-Service-Hub/skills/hub-client"

# 目标目录列表
TARGETS=(
    "$HOME/.openclaw/workspace-subagent1/skills"
    "$HOME/.openclaw/workspace-subagent2/skills"
    "$HOME/.openclaw/workspace-subagent3/skills"
    "$HOME/.openclaw/workspace-subagent4/skills"
)

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Sync hub-client skill to subagents${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查源目录
if [ ! -d "$SOURCE" ]; then
    echo "❌ 源目录不存在: $SOURCE"
    exit 1
fi

echo -e "源目录: ${GREEN}$SOURCE${NC}"
echo ""

# 同步到每个目标
for TARGET in "${TARGETS[@]}"; do
    SUBAGENT_NAME=$(basename "$(dirname "$TARGET")")
    
    # 创建目标目录（如果不存在）
    mkdir -p "$TARGET"
    
    # 复制 skill
    cp -r "$SOURCE" "$TARGET/"
    
    # 设置脚本可执行权限
    chmod +x "$TARGET/hub-client/scripts/"* 2>/dev/null || true
    
    echo -e "✅ ${GREEN}$SUBAGENT_NAME${NC} ← hub-client 已更新"
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  同步完成！${NC}"
echo -e "${GREEN}========================================${NC}"