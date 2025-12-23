# LangGraph 工作流图构建器
from langgraph.graph import StateGraph, END
from typing import Callable, Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class WorkflowGraphBuilder:
    """LangGraph 工作流图构建器
    
    职责：
    - 创建和管理 StateGraph 实例
    - 提供统一的节点、边、条件路由添加接口
    - 编译并返回可执行的图
    
    使用示例：
        builder = WorkflowGraphBuilder(state_schema=WorkflowState)
        builder.add_node("intent_analysis", intent_analysis_node)
        builder.add_node("llm_call", llm_call_node)
        builder.add_edge("intent_analysis", "llm_call")
        builder.add_edge("llm_call", END)
        builder.set_entry_point("intent_analysis")
        graph = builder.compile()
    """
    
    def __init__(self, state_schema: type):
        """初始化图构建器
        
        Args:
            state_schema: 状态结构类型（TypedDict）
        """
        self.state_schema = state_schema
        self.graph = StateGraph(state_schema)
        self.nodes: Dict[str, Callable] = {}
        self.entry_point: Optional[str] = None
        logger.info(f"WorkflowGraphBuilder 初始化完成，状态类型: {state_schema.__name__}")
    
    def add_node(self, name: str, func: Callable) -> "WorkflowGraphBuilder":
        """添加节点到图中
        
        Args:
            name: 节点名称（唯一标识）
            func: 节点执行函数，签名为 func(state: StateSchema) -> dict
            
        Returns:
            self，支持链式调用
        """
        if name in self.nodes:
            logger.warning(f"节点 '{name}' 已存在，将被覆盖")
        
        self.graph.add_node(name, func)
        self.nodes[name] = func
        logger.info(f"添加节点: {name}")
        return self
    
    def add_edge(self, from_node: str, to_node: str) -> "WorkflowGraphBuilder":
        """添加普通边（无条件直接跳转）
        
        Args:
            from_node: 起始节点名称
            to_node: 目标节点名称（可以是 END）
            
        Returns:
            self，支持链式调用
        """
        self.graph.add_edge(from_node, to_node)
        logger.info(f"添加边: {from_node} -> {to_node}")
        return self
    
    def add_conditional_edges(
        self,
        source: str,
        condition: Callable,
        mapping: Dict[str, str]
    ) -> "WorkflowGraphBuilder":
        """添加条件边（根据条件函数返回值选择路径）
        
        Args:
            source: 起始节点名称
            condition: 条件函数，签名为 condition(state) -> str
                      返回值应匹配 mapping 中的键
            mapping: 条件返回值到目标节点的映射
                    例如 {"continue": "next_node", "end": END}
            
        Returns:
            self，支持链式调用
        """
        self.graph.add_conditional_edges(source, condition, mapping)
        logger.info(f"添加条件边: {source} -> {list(mapping.values())}")
        return self
    
    def set_entry_point(self, node_name: str) -> "WorkflowGraphBuilder":
        """设置图的入口节点
        
        Args:
            node_name: 入口节点名称
            
        Returns:
            self，支持链式调用
        """
        if node_name not in self.nodes:
            raise ValueError(f"入口节点 '{node_name}' 不存在，请先添加该节点")
        
        self.graph.set_entry_point(node_name)
        self.entry_point = node_name
        logger.info(f"设置入口节点: {node_name}")
        return self
    
    def compile(self, checkpointer=None) -> Any:
        """编译图为可执行对象
        
        Args:
            checkpointer: 可选的检查点保存器（用于状态持久化）
            
        Returns:
            编译后的可执行图
        """
        if not self.entry_point:
            raise ValueError("未设置入口节点，请先调用 set_entry_point()")
        
        logger.info("开始编译工作流图...")
        compiled_graph = self.graph.compile(checkpointer=checkpointer)
        logger.info(f"✅ 工作流图编译成功，包含 {len(self.nodes)} 个节点")
        return compiled_graph
    
    def get_node_names(self) -> List[str]:
        """获取所有已添加的节点名称
        
        Returns:
            节点名称列表
        """
        return list(self.nodes.keys())
    
    def validate(self) -> bool:
        """验证图的有效性
        
        Returns:
            True 如果图配置有效，否则抛出异常
        """
        if not self.nodes:
            raise ValueError("图中没有任何节点")
        
        if not self.entry_point:
            raise ValueError("未设置入口节点")
        
        logger.info("图验证通过")
        return True
