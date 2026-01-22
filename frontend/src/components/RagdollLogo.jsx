import React from 'react'
import ragdollPhoto from '../assets/ragdoll-cat.jpg'

export default function RagdollLogo({ className = "w-8 h-8" }) {
  return (
    <img 
      src={ragdollPhoto} 
      alt="Ragdoll cat" 
      className={`${className} rounded-full object-cover`}
      style={{ objectPosition: 'center top' }}
    />
  )
}
