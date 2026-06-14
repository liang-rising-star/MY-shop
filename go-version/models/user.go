package models

import "time"

type UserLevel int

const (
	LevelNormal  UserLevel = 0
	LevelSilver  UserLevel = 1
	LevelGold    UserLevel = 2
	LevelDiamond UserLevel = 3
)

type User struct {
	ID        uint      `gorm:"primaryKey" json:"id"`
	Username  string    `gorm:"uniqueIndex;size:50;not null" json:"username"`
	Password  string    `gorm:"not null" json:"-"`
	Email     string    `gorm:"size:100" json:"email"`
	Level     UserLevel `gorm:"default:0" json:"level"`
	Points    int       `gorm:"default:0" json:"points"`
	IsAdmin   bool      `gorm:"default:false" json:"is_admin"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}
