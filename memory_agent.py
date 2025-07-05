from letta_client import AgentState, EmbeddingConfig, Letta, MessageCreate, MessageCreateContent, TextContent, ImageContent
from letta_client.types.agent_state import AgentState
from typing import Union
from letta_client import Base64Image, ImageContent, TextContent



SUPPORTED_MEDIA_TYPES = {"image/jpeg", "image/png"}

class MemoryAgent:
    def __init__(self, recipient: str):
        self.llm_model_name = "gpt-4.1-mini"
        self.recipient = recipient
        self.chat_id = recipient.replace("@", "_").replace(".", "_")
        self.client = Letta(base_url="http://localhost:8283")
        self.agent: AgentState = self.get_agent()
        
    
    def get_models(self):
        models = self.client.models.list()
        for model in models:
            if model.model == self.llm_model_name:
                return model
        raise ValueError(f"Model {self.llm_model_name} not found in available models.")
    
    def get_agent(self) -> AgentState:
        agents = self.client.agents.list(name=self.chat_id)
        return agents[0] if agents else self.set_agent()
    
    def set_agent(self) -> AgentState:
        return self.client.agents.create(
            name=self.chat_id,
            llm_config=self.get_models(),
            embedding_config=EmbeddingConfig(
                embedding_endpoint_type="openai",
                embedding_model="text-embedding-3-small",
                embedding_dim=1024,
            )
        )
        
    def send_message(self, whatsapp_msg):
        content: list[Union[TextContent, ImageContent]] = []
        
        if whatsapp_msg.has_media and whatsapp_msg.media.type in SUPPORTED_MEDIA_TYPES:
            content.append(ImageContent(
                source=Base64Image(
                    type= "base64",
                    media_type= whatsapp_msg.media.type,
                    data= whatsapp_msg.media.base64
                )
            ))
        if whatsapp_msg.quoted:
            if whatsapp_msg.quoted.type == "chat":
                content.append(TextContent(text=f"{whatsapp_msg.message}\n\n(Quoted): {whatsapp_msg.quoted.body}"))
            else:
                content.append(TextContent(text=f"{whatsapp_msg.message}"))
            if whatsapp_msg.quoted.type == "image" and whatsapp_msg.quoted.mimetype in SUPPORTED_MEDIA_TYPES:
                content.append(ImageContent(
                    source=Base64Image(
                        type= "base64",
                        media_type= whatsapp_msg.quoted.mimetype,
                        data= whatsapp_msg.quoted.base64_data)
                ))
                
        response = self.client.agents.messages.create(
            agent_id=self.agent.id,
            messages=[MessageCreate(role="user", content=content)]
        )
        
        assistant_reply = next(m for m in response.messages if m.message_type == "assistant_message")
        # print(f"Assistant Reply: {assistant_reply.content}")
        return assistant_reply.content
