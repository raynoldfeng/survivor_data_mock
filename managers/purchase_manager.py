# managers/purchase_manager.py
from basic_types.base_object import BaseObject
from basic_types.enums import *
from loader.purchase_config import PurchaseConfig
from .message_bus import Message, MessageType
from common import *


class PurchaseManager(BaseObject):
    _instance = None

    def __new__(cls, purchase_configs: Dict[str, PurchaseConfig], game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.game.purchase_manager = cls._instance
            cls._instance.purchase_configs = purchase_configs

            # 订阅购买请求事件
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_PURCHASE_REQUEST, cls._instance.handle_purchase_request)
        return cls._instance

    def handle_purchase_request(self, message: Message):
        """处理购买请求"""
        player_id = message.data["player_id"]
        package_name = message.data["package_name"]
        quantity = message.data["quantity"]

        player = self.game.player_manager.get_player_by_id(player_id)
        if not player:
            return

        # 获取购买项配置
        config = self.purchase_configs.get(package_name)
        if not config:
            self.game.log.warn(f"玩家 {player_id} 尝试购买未知物品: {package_name}")
            return

        # 检查金币是否足够
        total_price = config.price * quantity
        if player.gold < total_price:
            self.game.log.info(f"玩家 {player_id} 尝试购买 {package_name}，但金币不足。")
            return

        # 扣除金币
        player.gold -= total_price

        # 根据购买项类型进行处理
        if config.purchase_type == PurchaseType.RESOURCE:
            # 增加资源
            for resource_id, amount in config.content.items():
                player.add_resource(resource_id, amount * quantity)
            self.game.log.info(f"玩家 {player_id} 购买了 {quantity} 个 {config.package_name}，获得了资源: {config.content}")

            # 发送购买成功事件 (可选)
            self.game.message_bus.post_message(MessageType.PURCHASE_SUCCESS, {
                "player_id": player_id,
                "package_name": package_name,
                "quantity": quantity,
            }, self)

        elif config.purchase_type == PurchaseType.ITEM:
            # 处理物品 (预留)
            self.game.log.warn(f"玩家 {player_id} 尝试购买物品 {package_name}，但物品系统尚未实现。")
            pass