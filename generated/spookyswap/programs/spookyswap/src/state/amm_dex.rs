use anchor_lang::prelude::*;

/// Liquidity pool state (replaces Uniswap Pair contract)
/// EVM: reserve0, reserve1, totalSupply stored in Pair contract
/// Solana: Reserves are SPL token account balances, pool state in PDA
#[account]
#[derive(InitSpace)]
pub struct Pool {
    pub token_a_mint: Pubkey,
    pub token_b_mint: Pubkey,
    pub token_a_vault: Pubkey,    // EVM: stored implicitly in contract balance
    pub token_b_vault: Pubkey,    // Solana: explicit token accounts
    pub lp_mint: Pubkey,          // EVM: ERC-20 LP token
    pub fee_bps: u16,             // Fee in basis points
    pub authority: Pubkey,
    pub total_lp_supply: u64,
    pub bump: u8,
}

#[event]
pub struct PoolCreated {
    pub pool: Pubkey,
    pub token_a: Pubkey,
    pub token_b: Pubkey,
    pub fee_bps: u16,
}

#[event]
pub struct LiquidityAdded {
    pub pool: Pubkey,
    pub provider: Pubkey,
    pub amount_a: u64,
    pub amount_b: u64,
    pub lp_tokens: u64,
}

#[event]
pub struct SwapExecuted {
    pub pool: Pubkey,
    pub user: Pubkey,
    pub amount_in: u64,
    pub amount_out: u64,
    pub a_to_b: bool,
}
