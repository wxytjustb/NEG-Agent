<template>
	<view class="content">
        <image class="logo" src="../../static/logo.png"></image>
		<view>
            <text class="title">{{title}}</text>
        </view>
		
		<view class="test-section">
			<button type="primary" @click="testConnection">测试后端连接</button>
			<view class="result" v-if="result">
				<text :class="success ? 'success-text' : 'error-text'">{{ result }}</text>
			</view>
		</view>
	</view>
</template>

<script lang="ts">
  import Vue from 'vue';
  import { get } from '../../utls/require';

	export default Vue.extend({
		data() {
			return {
				title: 'Hello',
				result: '',
				success: false
			}
		},
		onLoad() {

		},
		methods: {
			async testConnection() {
				try {
					uni.showLoading({
						title: '连接中...'
					});
					
					const data: any = await get('/ping');
					
					uni.hideLoading();
					
					this.result = `成功: ${data.message}`;
					this.success = true;
					
					uni.showToast({
						title: '连接成功',
						icon: 'success'
					});
				} catch (error: any) {
					uni.hideLoading();
					
					this.result = `失败: ${error.message}`;
					this.success = false;
					
					uni.showToast({
						title: '连接失败',
						icon: 'error'
					});
				}
			}
		}
	});
</script>

<style>
	.content {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 40rpx;
	}

	.logo {
		height: 200rpx;
		width: 200rpx;
		margin: 200rpx auto 50rpx auto;
	}

	.text-area {
		display: flex;
		justify-content: center;
	}

	.title {
		font-size: 36rpx;
		color: #8f8f94;
	}
	
	.test-section {
		margin-top: 60rpx;
		width: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
	}
	
	.test-section button {
		width: 80%;
		margin-bottom: 30rpx;
	}
	
	.result {
		margin-top: 20rpx;
		padding: 20rpx;
		background-color: #f5f5f5;
		border-radius: 10rpx;
		width: 80%;
	}
	
	.success-text {
		color: #07c160;
		font-size: 28rpx;
	}
	
	.error-text {
		color: #fa5151;
		font-size: 28rpx;
	}
</style>
