from letta_client import EmbeddingConfig, Letta, LlmConfig, MessageCreate


class MemoryAgent:
    def __init__(self, base_url: str ="http://localhost:8283"):
        self.client = Letta(base_url=base_url)
    
    def get_models(self, name="gpt-4.1-mini"):
        models = self.client.models.list()
        if not models:
            raise ValueError(f"No models found with name: {name}")
        for model in models:
            if model.model == name:
                return model
    
    def get_agent(self, chat_id: str):
        agents = self.client.agents.list(name=chat_id)
        if agents:
            agent = agents[0]
        else:
            agent =  self.set_agent(chat_id)
        return agent
    
    def set_agent(self, chat_id: str):
        agent = self.client.agents.create(
            name=chat_id,
            llm_config=self.get_models(),
            embedding_config=EmbeddingConfig(embedding_endpoint_type="openai",
                                             embedding_model="text-embedding-3-small",
                                             embedding_dim=1024,)
            )
        return agent
        
    def send_message(self, payload: dict):
        chat_id = payload.get("to", "DEFAULT_CHAT_ID")
        normalized_chat_id:str = chat_id.replace("@", "_").replace(".", "_")
        message = payload.get("body", "").strip()
        response = self.client.agents.messages.create(
            agent_id=self.get_agent(normalized_chat_id).id,
            messages=[
            MessageCreate(role="user",
                          content=message
                          )
            ]
        )
        
        assistant_reply = next(
            m for m in response.messages if m.message_type == "assistant_message"
        )
        print(f"Assistant Reply: {assistant_reply.content}")
        return assistant_reply.content
        
        
        

if __name__ == "__main__":
    memory_agent = MemoryAgent()
    agent = memory_agent.get_agent("test_agent1211111")    
    memory_agent.send_message(agent_id=agent.id,
                              message="Hello, this is a test message."
                              )