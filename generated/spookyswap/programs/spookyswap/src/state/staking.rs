use anchor_lang::prelude::*;

/// Staking pool configuration
/// EVM: StakingRewards contract state
/// Solana: PDA account with reward tracking
#[account]
#[derive(InitSpace)]
pub struct StakingPool {
    pub authority: Pubkey,
    pub staking_mint: Pubkey,
    pub reward_mint: Pubkey,
    pub reward_rate: u64,              // Rewards per second
    pub total_staked: u64,
    pub last_update_time: i64,         // EVM: lastUpdateTime (block.timestamp)
    pub reward_per_token_stored: u128, // Accumulated rewards per token
    pub bump: u8,
}

/// Per-user stake info
/// EVM: mapping(address => UserInfo)
/// Solana: Separate PDA per user (derived from user pubkey)
#[account]
#[derive(InitSpace)]
pub struct UserStake {
    pub user: Pubkey,
    pub amount: u64,                          // EVM: balanceOf[user]
    pub rewards_earned: u64,                  // Unclaimed rewards
    pub reward_per_token_paid: u128,          // Last checkpoint
}

#[event]
pub struct Staked {
    pub user: Pubkey,
    pub amount: u64,
}

#[event]
pub struct RewardsClaimed {
    pub user: Pubkey,
    pub amount: u64,
}
