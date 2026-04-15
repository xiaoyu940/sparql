.PHONY: install test verify clean

# 默认目标
all: install verify

# 安装 pgrx 扩展
install:
	cargo pgrx install --release

# 运行自动化验证测试（每次安装后自动执行）
verify:
	@echo "=========================================="
	@echo "运行自动化 SPARQL 测试..."
	@echo "=========================================="
	@./tests/auto_verify.sh

# 完整流程：安装 + 验证
test: install verify
	@echo ""
	@echo "✅ 安装和验证完成"

# 快速验证（不重新安装）
quick-verify:
	@./tests/auto_verify.sh

# 清理
clean:
	cargo clean
