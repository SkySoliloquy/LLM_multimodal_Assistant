import time


class Memory:
    def __init__(self,
                 memu_client,
                 user_id,
                 agent_id,
                 user_name,
                 agent_name,):

        self.memu_client = memu_client
        self.conversation_buffer = []
        self.user_id = user_id
        self.user_name = user_name
        self.agent_id = agent_id
        self.agent_name = agent_name

    def menu_prompt(self):
        """获取全面的用户记忆，包括偏好和习惯"""
        all_categories = []

        # 1. 获取基础记忆（快速，~50ms）
        print("🔍 获取基础记忆...")
        try:
            default_categories = self.memu_client.retrieve_default_categories(
                user_id=self.user_id,
                agent_id=self.agent_id
            )
            if default_categories and hasattr(default_categories, 'categories'):
                all_categories.extend(default_categories.categories)
                print(f"✅ 获取到 {len(default_categories.categories)} 个基础类别")
        except Exception as e:
            print(f"❌ 获取基础记忆失败: {e}")

        # 2. 获取偏好相关记忆（稍慢，~200ms）
        preference_queries = [
            "preferences and habits",  # 偏好和习惯
            "likes and dislikes",  # 喜欢和不喜欢
            "routines and schedules"  # 日常安排
        ]

        for query in preference_queries:
            print(f"🔍 搜索偏好记忆: {query}")
            try:
                related_categories = self.memu_client.retrieve_related_clustered_categories(
                    user_id=self.user_id,
                    agent_id=self.agent_id,
                    category_query=query
                )

                if related_categories and hasattr(related_categories, 'clustered_categories'):
                    # 去重：只添加新的类别
                    existing_names = {cat.name for cat in all_categories}
                    for category in related_categories.clustered_categories:
                        if category.name not in existing_names:
                            all_categories.append(category)
                            existing_names.add(category.name)

                    print(f"✅ 从 '{query}' 找到 {len(related_categories.clustered_categories)} 个相关类别")

            except Exception as e:
                print(f"⚠️ 搜索 '{query}' 时出错: {e}")

        # 3. 构建完整的记忆上下文
        temp = self._build_context_with_memories({'categories': all_categories})
        print("即将载入的记忆："+temp)
        return temp

    def _build_context_with_memories(self, user_memories):
        """构建包含所有记忆的上下文"""
        base_prompt = "以下是关于用户的背景信息：\n\n"

        if user_memories and 'categories' in user_memories:
            # 按类别重要性排序：profile > preference > event > 其他
            category_priority = {
                'profile': 0,
                'preference': 1,
                'habit': 2,
                'event': 3
            }

            sorted_categories = sorted(
                user_memories['categories'],
                key=lambda x: category_priority.get(x.name.lower(), 999)
            )

            for category in sorted_categories:
                if hasattr(category, 'summary') and category.summary:
                    base_prompt += f"【{category.name}】：{category.summary}\n\n"
                elif isinstance(category, dict) and category.get('summary'):
                    base_prompt += f"【{category['name']}】：{category['summary']}\n\n"

        return base_prompt

    def _save_conversation_memory(self):
        try:
            response = self.memu_client.memorize_conversation(
                conversation=self.conversation_buffer,
                user_id=self.user_id,
                agent_id=self.agent_id,
                user_name=self.user_name,
                agent_name=self.agent_name
            )
            print(f"✅ 对话记忆已保存，任务ID: {response.task_id}")

            # 可选：等待任务完成
            #self._wait_for_task_completion(response.task_id)

        except Exception as e:
            print(f"❌ 保存对话记忆时出错: {e}")

    def _wait_for_task_completion(self, task_id, max_wait=30):
        """等待记忆处理任务完成"""
        import time
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                status = self.memu_client.get_task_status(task_id)
                print(f"📊 任务状态: {status.status}")

                if status.status in ['SUCCESS', 'FAILURE', 'REVOKED']:
                    if status.status == 'SUCCESS':
                        print("🎉 记忆处理完成！")
                    else:
                        print(f"⚠️ 记忆处理状态: {status.status}")
                    break

                time.sleep(2)
            except Exception as e:
                print(f"❌ 检查任务状态时出错: {e}")
                break