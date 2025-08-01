#!/bin/bash
echo "Phase 7-3 をロールバック中..."
cp backups/phase7/curriculum_helpers_original.py app/ai/curriculum_helpers.py
rm -rf app/services/ai
echo "ロールバック完了"