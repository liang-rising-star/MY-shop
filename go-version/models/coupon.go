package models

import "time"

type CouponType string

const (
	CouponPercent   CouponType = "percentage"
	CouponFixed     CouponType = "fixed"
)

type Coupon struct {
	ID        uint       `gorm:"primaryKey" json:"id"`
	Code      string     `gorm:"uniqueIndex;size:50;not null" json:"code"`
	Type      CouponType `gorm:"size:20;not null" json:"type"`
	Value     float64    `gorm:"not null" json:"value"`
	MinAmount float64    `gorm:"default:0" json:"min_amount"`
	MaxUses   int        `gorm:"default:0" json:"max_uses"`
	UsedCount int        `gorm:"default:0" json:"used_count"`
	ExpiresAt time.Time  `json:"expires_at"`
	CreatedAt time.Time  `json:"created_at"`
}

type UserCoupon struct {
	ID        uint       `gorm:"primaryKey" json:"id"`
	UserID    uint       `gorm:"index;not null" json:"user_id"`
	CouponID  uint       `gorm:"not null" json:"coupon_id"`
	Coupon    Coupon     `gorm:"foreignKey:CouponID" json:"coupon,omitempty"`
	UsedAt    *time.Time `json:"used_at,omitempty"`
	CreatedAt time.Time  `json:"created_at"`
}
