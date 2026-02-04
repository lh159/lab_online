#!/bin/bash

# 推送到 GitHub 的脚本
# 使用方法:
# 1. 在服务器上运行: scp -r root@你的服务器IP:/root/demo_1_confidence ~/demo_1_confidence
# 2. 或者克隆仓库: git clone https://github.com/lh159/lab_online.git
# 3. 将服务器上的文件复制进去
# 4. 运行此脚本

echo "=== ASR 置信度展示系统 - GitHub 推送脚本 ==="
echo ""
echo "步骤 1: 配置 Git 用户信息"
read -p "请输入你的 GitHub 用户名: " username
read -p "请输入你的邮箱: " email

git config --global user.name "$username"
git config --global user.email "$email"

echo ""
echo "步骤 2: 添加远程仓库"
git remote add origin https://github.com/lh159/lab_online.git

echo ""
echo "步骤 3: 重命名分支为 main"
git branch -M main

echo ""
echo "步骤 4: 推送到 GitHub"
echo "如果需要认证，请使用以下方法之一:"
echo ""
echo "方法 A - 使用 Personal Access Token:"
echo "  1. 访问 https://github.com/settings/tokens"
echo "  2. 生成一个新 token (需要有 repo 权限)"
echo "  3. 运行: git push -u origin main"
echo "     然后输入用户名和 token 作为密码"
echo ""
echo "方法 B - 使用 GitHub CLI:"
echo "  gh auth login"
echo "  gh repo sync"
echo "  git push"
echo ""
echo "方法 C - 如果已配置 SSH:"
echo "  git remote set-url origin git@github.com:lh159/lab_online.git"
echo "  git push -u origin main"

echo ""
echo "当前状态:"
git status
