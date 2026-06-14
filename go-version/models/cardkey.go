package models

import "time"

type CardKeyStatus string

const (
	CardKeyAvailable CardKeyStatus = "available"
	CardKeySold      CardKeyStatus = "sold"
	CardKeyExpired   CardKeyStatus = "expired"
)

type CardKey struct {
	ID        uint          `gorm:"primaryKey" json:"id"`
	ProductID uint          `gorm:"index;not null" json:"product_id"`
	Key       string        `gorm:"type:text;not null" json:"key"`
	Status    CardKeyStatus `gorm:"size:20;default:available" json:"status"`
	OrderID   *uint         `json:"order_id,omitempty"`
	SoldAt    *time.Time    `json:"sold_at,omitempty"`
	CreatedAt time.Time     `json:"created_at"`
}
